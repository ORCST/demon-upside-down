"""Build the K4 redraw + explicit K5 offset revision, keeping v01 immutable."""
import copy,hashlib,json,shutil
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from prep_sprites import snap,outline,denoise,PALETTE
from fix_pose_scale import SKIN,CREAM,color_mask

ROOT=Path(__file__).resolve().parent.parent
POSES=ROOT/'art_source/reference/poses'
OLD=POSES/'heavy_combo';OUT=POSES/'heavy_combo_v02'
ATT=POSES/'_codex/hc1_v02_attempts'
BG=(36,28,52)
FONT=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def native(path):
    a=np.array(Image.open(path).convert('RGBA').resize((256,256),Image.Resampling.BOX))
    a[...,:3]=snap(a[...,:3]);a[...,3]=(a[...,3]>=128).astype(np.uint8)*255
    return outline(denoise(a))

def muzzle(a):
    n,labels,stats,centers=cv2.connectedComponentsWithStats(color_mask(a,CREAM).astype(np.uint8),8)
    i=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
    return {'bbox':[int(v) for v in stats[i,:4]],'center':[float(v) for v in centers[i]]}

def head_span(a):
    m=muzzle(a);line=round(m['center'][1]+5)
    mask=color_mask(a,SKIN|CREAM|{(0xdd,0x95,0x86),(0xf2,0xba,0xa3)})
    mask[line+1:]=False;y,x=np.where(mask)
    return int(x.max()-x.min()+1)

def shift(a,dx,dy):
    out=np.zeros_like(a)
    x0=max(0,dx);x1=min(256,256+dx);y0=max(0,dy);y1=min(256,256+dy)
    out[y0:y1,x0:x1]=a[y0-dy:y1-dy,x0-dx:x1-dx]
    assert int((out[...,3]>0).sum())==int((a[...,3]>0).sum()),'Translation clipped sprite'
    return out

def foot_interval(a):
    # Brown hoof pixels only: the sword tip or a low belly must not become a foot.
    brown={(0x3f,0x2b,0x25),(0x5b,0x40,0x2d),(0x7e,0x5b,0x3b),(0xa7,0x81,0x50)}
    mask=color_mask(a,brown)&(np.indices(a.shape[:2])[0]>=204)
    ys,xs=np.where(mask)
    if not xs.size:raise ValueError('No brown hoof pixels on ground band')
    x=np.unique(xs);gaps=np.where(np.diff(x)>2)[0]
    front=x[gaps[-1]+1:] if gaps.size else x
    return [int(front.min()),int(front.max())]

def stage_image(a,offset=(0,0)):
    return Image.fromarray(shift(a,*offset)) if offset!=(0,0) else Image.fromarray(a)

def rgb(a,offset=(0,0)):
    im=stage_image(a,offset);bg=Image.new('RGBA',im.size,BG+(255,));bg.alpha_composite(im)
    return bg.convert('RGB')

def gif(path,seq,images,crop=False,ending_hold=0):
    entries=seq['attack']+seq['recover']
    if ending_hold:entries=entries+[{'pose':'idle_tail','hold':ending_hold}]
    frames=[];ticks=[0];elapsed=0
    for e in entries:
        im=rgb(images[e['pose']],tuple(seq['offset_px'].get(e['pose'],[0,0])))
        if crop:im=im.crop((16,88,240,224))
        frames.append(im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST))
        elapsed+=e['hold'];ticks.append(round(elapsed*100/seq['fps'])*10)
    durations=[b-a for a,b in zip(ticks,ticks[1:])]
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2,optimize=False)
    return {'file':path.name,'duration_ms':sum(durations),'nominal_units':elapsed,'entries':len(entries),'ending_idle_preview_only':ending_hold}

def main():
    OUT.mkdir(exist_ok=True)
    protected={str(p.relative_to(ROOT)):sha(p) for p in list(OLD.rglob('*'))+list(POSES.glob('niulai_*.png')) if p.is_file()}
    base=np.array(Image.open(POSES/'niulai_idle_tail_native.png').convert('RGBA'))
    raw=native(ATT/'k4_a3_raw.png')
    scale=head_span(base)/head_span(raw)
    small=Image.fromarray(raw).resize((round(256*scale),)*2,Image.Resampling.BOX)
    a=np.zeros((256,256,4),np.uint8);b=np.array(small);a[:b.shape[0],:b.shape[1]]=b
    a[...,:3]=snap(a[...,:3]);a[...,3]=(a[...,3]>=128).astype(np.uint8)*255;a=outline(denoise(a))
    sy,sx=np.where(a[...,3]>0);a=shift(a,0,207-int(sy.max()))
    front=foot_interval(a);a=shift(a,round(125-sum(front)/2),0)
    a[a[...,3]==0,:3]=0
    Image.fromarray(a).save(OUT/'niulai_hc1_k4_native.png')
    Image.fromarray(a).resize((1024,1024),Image.Resampling.NEAREST).save(OUT/'niulai_hc1_k4_x4.png')
    # v02 is a self-contained native bundle. Accepted artwork is copied unchanged.
    old_seq=json.loads((OLD/'hc1_sequence.json').read_text(encoding='utf-8'))
    for name,path in old_seq['pose_paths'].items():
        if name!='hc1_k4':shutil.copy2(OLD/path,OUT/Path(path).name)
    images={name:np.array(Image.open(OUT/Path(path).name).convert('RGBA')) for name,path in old_seq['pose_paths'].items()}
    seq=copy.deepcopy(old_seq);seq.update(version='hc1_v02',status='candidate_pending_user_review',art_changes=['hc1_k4 redraw'],offset_px={name:([15,0] if name=='hc1_k5' else [0,0]) for name in images},offset_note='Offsets are native canvas translations for artwork registration, not gameplay root motion. K5 PNG is byte-identical to v01: apply [15,0] ONCE. No offset is baked into that PNG.',root_motion_px_estimate=None)
    seq['pose_paths']={name:Path(path).name for name,path in seq['pose_paths'].items()}
    (OUT/'hc1_sequence.json').write_text(json.dumps(seq,ensure_ascii=False,indent=2),encoding='utf-8')
    suggested=copy.deepcopy(seq)
    suggested['status']='devin_timing_proposal_pending_in_game_tuning'
    suggested['attack']=[{'pose':'hc1_'+name,'hold':hold} for name,hold in [('k1',1),('k2',1),('k4',2),('k5',1),('k6',3)]]
    suggested['recover']=[{'pose':'hc1_c1','hold':2},{'pose':'hc1_c2','hold':1}]
    suggested['hit_after']='hc1_k5';suggested['hit_unit_index']=5
    suggested['cancel_from']={'pose':'hc1_k6','hold_index':1}
    suggested['cancel_until']={'pose':'hc1_c1','hold_index':1}
    suggested['input_buffer_from']='hc1_k5';suggested['index_base']=0
    suggested['return_to_idle']='idle_tail'
    suggested['timing_note']='Devin review proposal only; no opening/closing idle hold, K3 retained as spare but omitted from playback. K6 second held unit means hold_index=1.'
    (OUT/'hc1_timing_suggested.json').write_text(json.dumps(suggested,ensure_ascii=False,indent=2),encoding='utf-8')
    gif_stats=[gif(OUT/'hc1_preview.gif',seq,images),gif(OUT/'hc1_preview_closeup.gif',seq,images,True),gif(OUT/'hc1_devin_timing_preview.gif',suggested,images,True),gif(OUT/'hc1_devin_timing_with_idle.gif',suggested,images,True,6)]
    # Same timing before/after isolates artwork and registration changes.
    before=np.array(Image.open(OLD/'niulai_hc1_k4_native.png').convert('RGBA'))
    compare=Image.new('RGB',(4*512,384),BG);draw=ImageDraw.Draw(compare)
    comparisons=[('v01 K4',before,(0,0)),('v02 K4',a,(0,0)),('v01 K5',images['hc1_k5'],(0,0)),('v02 K5 offset +15',images['hc1_k5'],(15,0))]
    for i,(title,img,offset) in enumerate(comparisons):
        crop=rgb(img,offset).crop((32,128,192,224)).resize((512,307),Image.Resampling.NEAREST)
        compare.paste(crop,(i*512,52));draw.text((i*512+12,12),title,font=FONT,fill='white')
    compare.save(OUT/'hc1_revision_compare.png')
    names=['idle_tail','hc1_k1','hc1_k2','hc1_k3','hc1_k4','hc1_k5','hc1_k6','hc1_c1','hc1_c2'];refs=[0,3,5,6,8,10,12,None,None]
    sheet=Image.new('RGB',(len(names)*256,440),BG);draw=ImageDraw.Draw(sheet)
    for i,(name,r) in enumerate(zip(names,refs)):
        label=name.replace('hc1_','').upper();draw.text((i*256+8,8),label+(f' / R{r:03d}' if r is not None else ' / 收招'),font=FONT,fill='white')
        if r is not None:
            ref=Image.open(ROOT/f'art_source/reference/pose_refs/heavy_combo/R{r:03d}.png').crop((16,180,640,500)).resize((256,131),Image.Resampling.LANCZOS)
            sheet.paste(ref,(i*256,40))
        crop=rgb(images[name],tuple(seq['offset_px'][name])).crop((0,96,256,224))
        sheet.paste(crop,(i*256,230))
    sheet.save(OUT/'hc1_compare.png')
    allowed={tuple(map(int,c)) for c in PALETTE}
    checks=[]
    for name,img in images.items():
        shown=shift(img,*seq['offset_px'][name]);y,x=np.where(shown[...,3]>0)
        colors={tuple(map(int,c)) for c in np.unique(shown[shown[...,3]>0][:,:3],axis=0)}
        assert colors<=allowed and set(map(int,np.unique(shown[...,3])))<={0,255}
        assert y.max()==207 and x.min()>=8 and x.max()<=247
        unchanged=name=='hc1_k4' or sha(OUT/seq['pose_paths'][name])==sha(OLD/old_seq['pose_paths'][name])
        assert unchanged
        checks.append({'pose':name,'display_bbox':[int(x.min()),int(y.min()),int(x.max()),int(y.max())],'front_hoof_brown_core_interval':foot_interval(shown),'muzzle':muzzle(shown),'head_span':head_span(shown) if name in ['idle_tail','hc1_k4'] else None,'skin_pixels':int(color_mask(shown,SKIN).sum()),'palette_valid':True,'unchanged_native_art_except_k4':unchanged})
    assert all(sha(ROOT/path)==value for path,value in protected.items())
    report={'tool':'built-in image_gen','new_generation_calls':3,'lifetime_k4_calls':4,'selected':'k4_a3_raw.png','head_uniform_scale':scale,'k4_head_span_idle':head_span(base),'k4_head_span_export':head_span(a),'k4_body_height_px':int(np.where(a[...,3]>0)[0].max()-np.where(a[...,3]>0)[0].min()+1),'body_height_limit':'Head-size normalization is preserved; crouch does not fully reach review target of ~43px. Candidate requires visual re-review.','k5_offset_px':[15,0],'k5_offset_baked':False,'v01_and_root_pose_files_unchanged':True,'protected_file_count':len(protected),'poses':checks,'gifs':gif_stats}
    (OUT/'hc1_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ATT/'protected_files.json').write_text(json.dumps(protected,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
