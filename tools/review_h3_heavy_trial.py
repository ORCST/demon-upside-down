"""Build silent, neutral-background review media without modifying production sprites."""
import json
from pathlib import Path
import av
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from prep_sprites import key_green

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'art_source/minimax/heavy_combo_trial_v01'
paths=sorted((OUT/'frames').glob('*.png'))
if not paths:raise SystemExit('No generated frames yet')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
movie=av.open(str(OUT/'review_silent.mp4'),'w',options={'movflags':'+faststart'})
stream=movie.add_stream('libx264',rate=24);stream.width=768;stream.height=768;stream.pix_fmt='yuv420p';stream.options={'crf':'18'}
indices=set(round(i*(len(paths)-1)/11) for i in range(12));thumbs=[];stats=[]
for i,p in enumerate(paths):
    rgb=np.array(Image.open(p).convert('RGB'));alpha=key_green(rgb)
    bg=np.full(rgb.shape,[45,50,62],dtype=np.uint8)
    composed=(rgb*alpha[...,None]+bg*(1-alpha[...,None])).astype(np.uint8)
    im=Image.fromarray(composed)
    d=ImageDraw.Draw(im);d.text((18,15),'H3 动作试片 v01 · 文本近似参考',font=font,fill='white')
    d.text((18,46),f'{i/24:.2f}s · 固定构图 / 未接入游戏',font=font,fill='#b9c7d9')
    frame=av.VideoFrame.from_image(im);frame.pts=i
    for packet in stream.encode(frame):movie.mux(packet)
    if i in indices:
        thumb=im.resize((256,256),Image.Resampling.LANCZOS)
        ImageDraw.Draw(thumb).text((8,230),f'F{i:03d}',font=font,fill='white');thumbs.append(thumb)
    y,x=np.where(alpha>0.5)
    stats.append({'frame':i,'bbox': [int(x.min()),int(y.min()),int(x.max()),int(y.max())] if x.size else None,'foreground_pixels':int(x.size)})
for packet in stream.encode():movie.mux(packet)
movie.close()
sheet=Image.new('RGB',(1024,768),'#2d323e')
for i,im in enumerate(thumbs):sheet.paste(im,(i%4*256,i//4*256))
sheet.save(OUT/'contact_sheet.jpg',quality=94)
(OUT/'frame_stats.json').write_text(json.dumps(stats,indent=2))
checks=[]
for p in OUT.glob('*.mp4'):
    with av.open(str(p)) as c:
        n=sum(1 for _ in c.decode(video=0))
        checks.append({'file':p.name,'decoded_frames':n,'expected_frames':len(paths),'passed':n==len(paths)})
(OUT/'verification.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
