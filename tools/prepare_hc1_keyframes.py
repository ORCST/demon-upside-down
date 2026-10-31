"""Prepare and package only the generated hc1 keyframes; never writes assets/.

Run prepare, then fix_pose_scale.py --poses hc1_k1 ... hc1_c2, then package.
Generation is done with image_gen. This script performs the pixel export and
contact-sheet/GIF assembly explicitly requested in the first-cut plan.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from prep_sprites import snap,denoise,outline,PALETTE
from fix_pose_scale import color_mask,SKIN,CREAM,body_scale

ROOT=Path(__file__).resolve().parent.parent
POSES=ROOT/'art_source/reference/poses'
ATT=POSES/'_codex/hc1_attempts'
OUT=POSES/'heavy_combo'
REFS=ROOT/'art_source/reference/pose_refs/heavy_combo'
KEYS=['k1','k2','k3','k4','k5','k6','c1','c2']
BG=(36,28,52)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare():
    OUT.mkdir(exist_ok=True)
    old={str(p.relative_to(ROOT)):sha(p) for p in POSES.glob('niulai_*.png') if '_hc1_' not in p.name}
    (ATT/'protected_files_before.json').write_text(json.dumps(old,indent=2))
    manifest=json.loads((ATT/'generation_manifest.json').read_text())
    for item in manifest['items']:
        key=item['key']
        src=ROOT/item['raw_path']
        original=Image.open(src).convert('RGBA')
        small=np.array(original.resize((256,256),Image.Resampling.BOX))
        small[...,:3]=snap(small[...,:3])
        small[...,3]=(small[...,3]>=128).astype(np.uint8)*255
        native=outline(denoise(small))
        dest=POSES/'_codex'/f'niulai_hc1_{key}_native.png'
        Image.fromarray(native).save(dest)
        prompt=(ROOT/item['prompt_path']).read_text(encoding='utf-8')
        prompt+='\n\nOriginal image_gen output: '+item['raw_path']+'\nActual raw dimensions: '+str(original.size)+'\nPixel export: area downsample to 256x256, binary alpha, approved palette snap, existing denoise/outline. Original raw retained unchanged.\n'
        dest.with_suffix('.prompt.txt').write_text(prompt,encoding='utf-8')
    print('Prepared 8 derived native inputs; original raw generations retained.')

def composite(im,scale=1):
    bg=Image.new('RGBA',im.size,BG+(255,));bg.alpha_composite(im)
    return bg.convert('RGB').resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)

def package():
    manifest=json.loads((ATT/'generation_manifest.json').read_text())
    base=np.array(Image.open(POSES/'niulai_idle_tail_native.png').convert('RGBA'))
    metrics=[];images={'idle_tail':Image.fromarray(base)}
    approved={tuple(int(c) for c in row) for row in PALETTE}
    for item in manifest['items']:
        key=item['key'];p=POSES/f"niulai_hc1_{key}_native.png"
        a=np.array(Image.open(p).convert('RGBA'))
        skin=color_mask(a,SKIN);ys,xs=np.nonzero(skin)
        solid_y,solid_x=np.nonzero(a[...,3]>0)
        dx=round(112-xs.mean());dy=207-int(solid_y.max())
        if solid_x.min()+dx<8 or solid_x.max()+dx>247:
            raise SystemExit(f'{key}: anchored sprite exceeds safe canvas margin; inspect before accepting')
        shifted=np.zeros_like(a)
        x0=max(0,dx);x1=min(256,256+dx);y0=max(0,dy);y1=min(256,256+dy)
        shifted[y0:y1,x0:x1]=a[y0-dy:y1-dy,x0-dx:x1-dx]
        a=shifted
        a[a[...,3]==0,:3]=0
        im=Image.fromarray(a);im.save(p)
        im.resize((1024,1024),Image.Resampling.NEAREST).save(POSES/f'niulai_hc1_{key}_x4.png')
        shutil.copy2(p,OUT/p.name)
        shutil.copy2(POSES/'_codex'/p.with_suffix('.prompt.txt').name,POSES/p.with_suffix('.prompt.txt').name)
        images['hc1_'+key]=im
        sy,sx=np.nonzero(a[...,3]>0);skin_y,skin_x=np.nonzero(color_mask(a,SKIN))
        colors={tuple(int(c) for c in row) for row in np.unique(a[a[...,3]>0][:,:3],axis=0)}
        metrics.append({'pose':'hc1_'+key,'raw_size':list(Image.open(ROOT/item['raw_path']).size),'attempts':item.get('attempt',1),'reference_frame':item['reference_frame'],'native_size':[256,256],'alpha_values':list(map(int,np.unique(a[...,3]))),'colors_used':len(colors),'palette_valid':colors<=approved,'bbox':[int(sx.min()),int(sy.min()),int(sx.max()),int(sy.max())],'lowest_opaque_row':int(sy.max()),'skin_center_x':round(float(skin_x.mean()),2),'body_area_scale_vs_idle':round(body_scale(a,base,'hc1_'+key),4),'translation_px':[dx,dy],'foreground_pixels':int(len(sx))})
    attack=[{'pose':'idle_tail','hold':2}]+[{'pose':'hc1_'+k,'hold':h} for k,h in zip(KEYS[:6],[1,1,1,2,1,4])]
    recover=[{'pose':'hc1_c1','hold':2},{'pose':'hc1_c2','hold':2},{'pose':'idle_tail','hold':2}]
    seq={'attack':attack,'recover':recover,'fps':12,'hit_after':'hc1_k5','cancel_from':'hc1_k6','reference_hit_frame':11,'canvas':[256,256],'ground_y':208,'status':'candidate_pending_user_review','pose_paths':{name:('../../'+('niulai_idle_tail_native.png' if name=='idle_tail' else 'niulai_'+name+'_native.png')) for name in images},'root_motion_note':'Source is the in-place/non-RM version. Original root-motion distances cannot be recovered reliably. Character artwork is anchored in place. K4→K5 and K5→K6 displacement remain for Devin to tune; no invented pixel distance.','root_motion_px_estimate':None}
    # Paths are relative to this JSON, which is one directory below the pose PNGs.
    seq['pose_paths']={name:('niulai_idle_tail_native.png' if name=='idle_tail' else 'niulai_'+name+'_native.png') for name in images}
    (OUT/'hc1_sequence.json').write_text(json.dumps(seq,ensure_ascii=False,indent=2),encoding='utf-8')
    playback=attack+recover
    frames=[composite(images[x['pose']],3) for x in playback]
    ticks=[0];elapsed=0
    for x in playback:
        elapsed+=x['hold'];ticks.append(round(elapsed*100/12)*10)
    durations=[b-a for a,b in zip(ticks,ticks[1:])]
    frames[0].save(OUT/'hc1_preview.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2,optimize=False)
    closeups=[composite(images[x['pose']]).crop((16,88,240,224)).resize((672,408),Image.Resampling.NEAREST) for x in playback]
    closeups[0].save(OUT/'hc1_preview_closeup.gif',save_all=True,append_images=closeups[1:],duration=durations,loop=0,disposal=2,optimize=False)
    Image.fromarray(base).save(OUT/'niulai_idle_tail_native.png')
    labels=['K0','K1','K2','K3','K4','K5','K6','C1','C2'];names=['idle_tail']+['hc1_'+k for k in KEYS]
    refs=[0,3,5,6,8,10,12,None,None]
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
    sheet=Image.new('RGB',(9*256,560),BG);draw=ImageDraw.Draw(sheet)
    for j,(label,name,r) in enumerate(zip(labels,names,refs)):
        draw.text((j*256+8,6),label+(f' / R{r:03d}' if r is not None else ' / 收招设计'),font=font,fill='white')
        if r is not None:
            ref=Image.open(REFS/f'R{r:03d}.png').convert('RGB').resize((256,256),Image.Resampling.LANCZOS)
            sheet.paste(ref,(j*256,34))
        else:draw.text((j*256+20,140),'无白模参考',font=font,fill='#b9acc8')
        sheet.paste(composite(images[name]),(j*256,298))
    sheet.save(OUT/'hc1_compare.png')
    # Larger calf-only strip is convenient for judging the pixel silhouette.
    detail=Image.new('RGB',(9*256,256),BG)
    for j,name in enumerate(names):
        thumb=composite(images[name]).crop((32,96,224,224)).resize((256,170),Image.Resampling.NEAREST)
        detail.paste(thumb,(j*256,40));ImageDraw.Draw(detail).text((j*256+10,8),labels[j],font=font,fill='white')
    detail.save(OUT/'hc1_detail.png')
    protected=json.loads((ATT/'protected_files_before.json').read_text())
    unchanged=all((ROOT/p).exists() and sha(ROOT/p)==h for p,h in protected.items())
    assert unchanged,'An unrelated old pose changed'
    checks={'poses':metrics,'old_pose_files_unchanged':unchanged,'protected_old_pose_count':len(protected),'two_reference_images_supported':True,'frame_count_with_holds':sum(x['hold'] for x in playback),'nominal_seconds':sum(x['hold'] for x in playback)/12,'gif_durations_ms':durations,'gif_total_duration_ms':sum(durations),'closeup_common_crop':[16,88,240,224]}
    for m in metrics:
        assert m['palette_valid'] and m['lowest_opaque_row']==207
        assert set(m['alpha_values'])<={0,255}
        assert abs(m['skin_center_x']-112)<=0.51
    (OUT/'hc1_validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['prepare','package']);args=parser.parse_args()
    prepare() if args.stage=='prepare' else package()
