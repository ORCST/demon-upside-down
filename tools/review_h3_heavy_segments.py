"""Review heavy_combo_seg_v01: run each segment through prep_sprites' pixel pipeline
(without writing assets/ or clips.json) and build contact sheets + a chained preview GIF.

    py tools/review_h3_heavy_segments.py   (needs cv2: use system Python 311)
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from prep_sprites import key_green,drop_fx,keep_body,to_native,denoise,outline,CANVAS

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'art_source/minimax/heavy_combo_seg_v01'
CHAINS={'cut1_then_recover':['cut1','cut1_recover'],'cut1_then_cut2':['cut1','cut2']}
BG=(36,28,52,255)

def native_frames(seg:str,step:int=2)->list:
    files=sorted((OUT/seg/'frames').glob('*.png'))
    out=[]
    for f in files[::step]:
        rgb=np.array(Image.open(f).convert('RGB'));a=keep_body(drop_fx(rgb,key_green(rgb)))
        out.append(outline(denoise(to_native(rgb,a,(0.0,0.0),rgb.shape[1]/CANVAS))))
    return out

def show(img:np.ndarray,scale:int=3)->Image.Image:
    bg=Image.new('RGBA',(CANVAS,CANVAS),BG);bg.alpha_composite(Image.fromarray(img,'RGBA'))
    return bg.convert('RGB').resize((CANVAS*scale,CANVAS*scale),Image.NEAREST)

report={}
done={s.name:native_frames(s.name) for s in sorted(OUT.iterdir()) if (s/'frames').is_dir() and any((s/'frames').iterdir())}
for seg,nat in done.items():
    cols=8;rows=(len(nat)+cols-1)//cols;sheet=Image.new('RGB',(cols*256,rows*256),BG[:3])
    for k,img in enumerate(nat):
        t=show(img,1);ImageDraw.Draw(t).text((6,6),f'{seg} #{k}',fill='white');sheet.paste(t,(k%cols*256,k//cols*256))
    sheet.save(OUT/seg/'native_sheet.png')
    px=[int((n[...,3]>0).sum()) for n in nat]
    report[seg]={'native_frames':len(nat),'opaque_px_min':min(px),'opaque_px_max':max(px),'opaque_px_first':px[0]}
for chain,segs in CHAINS.items():
    if not all(s in done for s in segs):continue
    frames=done[segs[0]]+[f for s in segs[1:] for f in done[s][1:]]
    imgs=[show(f) for f in frames]
    imgs[0].save(OUT/f'{chain}.gif',save_all=True,append_images=imgs[1:],duration=83,loop=0)
    report[chain]={'gif_frames':len(imgs)}
(OUT/'review.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
