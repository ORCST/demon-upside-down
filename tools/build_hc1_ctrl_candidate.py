"""Build the Devin-reviewed first-cut candidate; local R010 alpha cleanup only.

No re-generation, global sprite-pipeline changes or game imports. Native files
come from the prior depth-proxy review; recovery comes from approved v02 art.
"""
import hashlib,json,shutil
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
from prep_sprites import PALETTE

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'art_source/minimax/heavy_combo_ctrl_v01/depth_proxy'
V02=ROOT/'art_source/reference/poses/heavy_combo_v02'
OUT=ROOT/'art_source/minimax/hc1_ctrl'
BG=(36,28,52,255)
SELECTED=[4,6,8,10,12,14,16]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def show(a,scale=3):
    bg=Image.new('RGBA',(256,256),BG);bg.alpha_composite(Image.fromarray(a,'RGBA'))
    return bg.convert('RGB').resize((256*scale,256*scale),Image.Resampling.NEAREST)

def clean_r010(a):
    # A reviewed, frame-specific ROI behind the calf; the muzzle is outside it.
    yy,xx=np.indices(a.shape[:2]);roi=(xx<92)&(yy>=145)&(yy<188)
    body_colors=np.array([[63,43,37],[91,64,45],[126,91,59],[167,129,80],[182,138,36],[232,184,48],[244,211,106]],np.uint8)
    warm=np.any(np.all(a[:,:,:3,None]==body_colors.T[None,None,:,:],axis=2),axis=2)
    seed=warm&(a[:,:,3]>0)&(xx>=76)
    near=cv2.dilate(seed.astype(np.uint8),np.ones((3,3),np.uint8))>0
    dark=np.all(a[:,:,:3]==[40,27,33],axis=2)
    protected=seed|(near&dark)
    removed=roi&(a[:,:,3]>0)&~protected
    result=a.copy();result[removed,3]=0
    # Retained RGB, body seed pixels and everything outside this small ROI stay exact.
    assert np.array_equal(result[:,:,:3],a[:,:,:3])
    assert np.array_equal(result[protected],a[protected])
    assert np.array_equal(result[~roi],a[~roi])
    return result,removed,protected,roi

def main():
    (OUT/'native').mkdir(parents=True,exist_ok=True);(OUT/'review').mkdir(exist_ok=True)
    poses={};paths={};offsets={};origins={};report={}
    for i in SELECTED:
        source=SRC/'native_review'/f'R{i:03d}.png';a=np.array(Image.open(source).convert('RGBA'));key=f'hc1_ctrl_r{i:03d}'
        if i==10:
            before=a.copy();a,removed,protected,roi=clean_r010(a)
            Image.fromarray(removed.astype(np.uint8)*255).save(OUT/'review/R010_removed_alpha.png')
            Image.fromarray(protected.astype(np.uint8)*255).save(OUT/'review/R010_protected_body.png')
            Image.fromarray(before).save(OUT/'review/R010_before_native.png')
            comp=Image.new('RGB',(1024,420),BG[:3]);dr=ImageDraw.Draw(comp);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
            for col,(n,label) in enumerate([(before,'原始像素化 R010'),(a,'只清剑光 R010')]):
                im=show(n,1).crop((10,140,138,214)).resize((512,296),Image.Resampling.NEAREST)
                comp.paste(im,(col*512,40));dr.text((col*512+12,12),label,font=font,fill='white')
            comp.save(OUT/'review/R010_cleanup_compare.png')
            report['R010_cleanup']={'roi_native':[0,145,92,188],'removed_foreground_pixels':int(removed.sum()),'protected_body_pixels':int(protected.sum()),'retained_RGB_unchanged':True,'outside_ROI_unchanged':True,'body_seed_pixels_unchanged':True,'method':'Frame-specific alpha mask; preserve body warm palette and adjacent dark outline, erase FX colors inside ROI; no body replacement or K5 substitution.'}
        target=OUT/'native'/f'{key}.png';Image.fromarray(a,'RGBA').save(target)
        poses[key]=a;paths[key]=target.relative_to(OUT).as_posix();offsets[key]=[0,-1] if i in [14,16] else [0,0]
        origins[key]={'source_reference_frame':i,'source_native':source.relative_to(ROOT).as_posix(),'source_native_sha256':sha(source),'source_raw_sha256':sha(SRC/'frames'/f'R{i:03d}.png')}
    for name in ['c1','c2']:
        key=f'hc1_{name}';source=V02/f'niulai_hc1_{name}_native.png';target=OUT/'native'/source.name
        shutil.copy2(source,target);poses[key]=np.array(Image.open(target).convert('RGBA'));paths[key]=target.relative_to(OUT).as_posix();offsets[key]=[0,0]
        origins[key]={'source':source.relative_to(ROOT).as_posix(),'source_sha256':sha(source),'byte_identical':sha(source)==sha(target)}
    idle_source=ROOT/'art_source/reference/poses/niulai_idle_tail_native.png';idle_target=OUT/'native/niulai_idle_tail_native.png';shutil.copy2(idle_source,idle_target)
    poses['idle_tail']=np.array(Image.open(idle_target).convert('RGBA'));paths['idle_tail']=idle_target.relative_to(OUT).as_posix();offsets['idle_tail']=[0,0]
    attack=[{'pose':f'hc1_ctrl_r{i:03d}','hold':h} for i,h in [(4,1),(6,1),(8,2),(10,1),(12,3)]]
    recover=[{'pose':'hc1_c1','hold':2},{'pose':'hc1_c2','hold':1}]
    sequence={'name':'hc1_ctrl','status':'candidate_pending_user_review','fps':12,'canvas':[256,256],'ground_y':208,'attack':attack,'recover':recover,'pose_paths':paths,'offset_px':offsets,
        'spare_poses':['hc1_ctrl_r014','hc1_ctrl_r016'],'hit_after':'hc1_ctrl_r010','hit_unit_index':5,'reference_hit_frame':11,
        'input_buffer_from':'hc1_ctrl_r010','input_buffer_tick':4,'cancel_from':{'pose':'hc1_ctrl_r012','hold_index':1},'cancel_until':{'pose':'hc1_c1','hold_index':1},
        'cancel_tick_range_inclusive':[6,9],'return_to_idle':'idle_tail','index_base':0,'playback_ticks':11,'duration_seconds':11/12,
        'root_motion_px_estimate':None,'offset_note':'Apply listed offsets ONCE; they are artwork registration, not gameplay root motion. R014/R016 are spare PNGs unchanged at native y208, use offset [0,-1] if selected. Timed playback uses R004/R006/R008/R010/R012, all naturally grounded at y207.',
        'handoff_mode':'Native frames for Devin to pack after user approval; no clips.json registration or prep_sprites game import in this delivery.',
        'origins':origins,'cleanup_note':'R010 only alpha cleanup; no sword drawn, no K5 replacement. Devin adds the slash effect in game.'}
    (OUT/'hc1_ctrl_sequence.json').write_text(json.dumps(sequence,ensure_ascii=False,indent=2),encoding='utf8')
    # No horizontal registration changes; preserve the generated head trajectory.
    rendered={}
    for key,a in poses.items():
        ox,oy=offsets[key];im=Image.fromarray(a);dst=Image.new('RGBA',(256,256));dst.alpha_composite(im,(ox,oy));rendered[key]=np.array(dst)
        solid=rendered[key][:,:,3]>0;y,x=np.where(solid)
        assert solid.any() and y.max()==207,(key,int(y.max()))
        assert set(np.unique(a[:,:,3]))<={0,255}
        cols=np.unique(a[a[:,:,3]>0,:3],axis=0)
        assert all(any(np.array_equal(c,p) for p in PALETTE) for c in cols)
        report[key]={'bbox_raw':[int(v) for v in Image.fromarray(a).getbbox()],'rendered_last_row':int(y.max()),'offset_px':offsets[key],'opaque_pixels':int(solid.sum()),'sha256':sha(OUT/paths[key])}
    timeline=[show(rendered[item['pose']]) for item in attack+recover for _ in range(item['hold'])]
    # GIF delays are centiseconds: cycle 80/80/90ms so total is 0.91s, close to 11/12.
    delays=[80,80,90,80,80,90,80,80,90,80,80]
    timeline[0].save(OUT/'hc1_ctrl_preview.gif',save_all=True,append_images=timeline[1:],duration=delays,loop=0,disposal=2)
    framed=[show(rendered['idle_tail'])]*6+timeline+[show(rendered['idle_tail'])]*6
    framed[0].save(OUT/'hc1_ctrl_with_idle.gif',save_all=True,append_images=framed[1:],duration=[80]*6+delays+[80]*6,loop=0,disposal=2)
    # Fixed crop only for viewing; native sprite positions and JSON stay unchanged.
    close=[im.crop((18*3,117*3,212*3,216*3)).resize((776,396),Image.Resampling.NEAREST) for im in timeline]
    close[0].save(OUT/'hc1_ctrl_preview_closeup.gif',save_all=True,append_images=close[1:],duration=delays,loop=0,disposal=2)
    close_idle=[im.crop((18*3,117*3,212*3,216*3)).resize((776,396),Image.Resampling.NEAREST) for im in framed]
    close_idle[0].save(OUT/'hc1_ctrl_with_idle_closeup.gif',save_all=True,append_images=close_idle[1:],duration=[80]*6+delays+[80]*6,loop=0,disposal=2)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18);keys=list(poses)
    sheet=Image.new('RGB',(5*384,2*408),BG[:3]);dr=ImageDraw.Draw(sheet)
    for k,key in enumerate(keys):
        im=show(rendered[key],1).resize((384,384),Image.Resampling.NEAREST);sheet.paste(im,(k%5*384,k//5*408+24));dr.text((k%5*384+8,k//5*408+2),key,font=font,fill='white')
    sheet.save(OUT/'hc1_ctrl_contact_sheet.png')
    report['summary']={'native_frames':len(poses),'selected_generated_frames':SELECTED,'played_generated_frames':[4,6,8,10,12],'source_position_preserved':True,'global_pipeline_changed':False,'ComfyUI_started':False,'game_assets_imported':False,'sequence_ticks':11,'gif_approx_duration_ms':sum(delays),'JSON_duration_seconds':11/12}
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report['summary'],indent=2));print('R010 removed',report['R010_cleanup']['removed_foreground_pixels'])

if __name__=='__main__':main()
