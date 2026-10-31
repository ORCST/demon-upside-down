"""Review raw generated control trials without importing into game assets."""
import argparse,json
from pathlib import Path
import av,numpy as np
from PIL import Image,ImageDraw,ImageFont
from prep_sprites import key_green,drop_fx,keep_body,to_native,denoise,outline

ROOT=Path(__file__).resolve().parent.parent
CONTROL=ROOT/'art_source/control/heavy_combo_v02_39f'
OUT=ROOT/'art_source/minimax/heavy_combo_ctrl_v01'
FONT=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)

def encode(path,frames,fps):
    with av.open(str(path),'w',options={'movflags':'+faststart'}) as c:
        s=c.add_stream('libx264',rate=fps);s.width,s.height=frames[0].size;s.pix_fmt='yuv420p';s.options={'crf':'16','preset':'fast'}
        for i,im in enumerate(frames):
            f=av.VideoFrame.from_image(im.convert('RGB'));f.pts=i
            for packet in s.encode(f):c.mux(packet)
        for packet in s.encode():c.mux(packet)

def run(variant,attempt=1,control_kind='depth'):
    d=OUT/(control_kind+'_'+variant+(f'_attempt{attempt:02d}' if attempt>1 else ''));files=sorted((d/'frames').glob('R*.png'))
    assert len(files)==39
    raw=[];native=[];metrics=[];union=[768,768,0,0]
    for i,f in enumerate(files):
        im=Image.open(f).convert('RGB');assert im.size==(768,768);rgb=np.array(im);raw.append(im)
        a=key_green(rgb);y,x=np.where(a>.5)
        if x.size:
            bbox=[int(x.min()),int(y.min()),int(x.max()),int(y.max())]
            union=[min(union[0],bbox[0]),min(union[1],bbox[1]),max(union[2],bbox[2]),max(union[3],bbox[3])]
        else:bbox=None
        cleaned=keep_body(drop_fx(rgb,a))
        n=outline(denoise(to_native(rgb,cleaned,(0.,0.),3.)))
        native.append(Image.fromarray(n))
        metrics.append({'frame':i,'raw_foreground_pixels':int((a>.5).sum()),'raw_bbox':bbox,'native_opaque_pixels':int((n[:,:,3]>0).sum()),
                        'green_background_fraction':float((a<.01).mean())})
    m=json.loads((CONTROL/'render_manifest.json').read_text(encoding='utf8'))
    cc=m['preview_common_crop']
    crop=[max(0,min(cc[0],union[0]-18)),max(0,min(cc[1],union[1]-18)),min(768,max(cc[2],union[2]+19)),min(768,max(cc[3],union[3]+19))]
    boards=[]
    for i,im in enumerate(raw):
        b=Image.new('RGB',(1152,420),'#171c26');dr=ImageDraw.Draw(b)
        src=Image.open(CONTROL/variant/'beauty'/f'R{i:03d}.png').convert('RGB')
        for col,(p,label) in enumerate([(src,'白模 '+variant),(im,'牛来生成原图')]):
            p=p.crop(crop);p.thumbnail((576,384),Image.Resampling.LANCZOS)
            b.paste(p,(col*576+(576-p.width)//2,34))
            dr.text((col*576+10,7),f'{label} / R{i:03d}',font=FONT,fill='white')
        boards.append(b)
    encode(d/'reference_vs_generated.mp4',boards,24)
    # Slower review copy is explicitly separate from all source-speed controls.
    encode(d/'reference_vs_generated_half_speed.mp4',boards,12)
    selected=[0,1,2,3,4,5,8,10,12,16,20,24,28,32,36,38]
    sheet=Image.new('RGB',(8*256,2*280),'#171c26');dr=ImageDraw.Draw(sheet)
    for k,i in enumerate(selected):
        thumb=raw[i].resize((256,256),Image.Resampling.LANCZOS)
        sheet.paste(thumb,(k%8*256,k//8*280+24));dr.text((k%8*256+6,k//8*280+3),f'R{i:03d}',font=FONT,fill='white')
    sheet.save(d/'raw_contact_sheet.png')
    sheet=Image.new('RGB',(8*256,3*280),'#241c34');dr=ImageDraw.Draw(sheet)
    previews=[]
    for k,i in enumerate(range(0,39,2)):
        n=Image.new('RGBA',(256,256),(36,28,52,255));n.alpha_composite(native[i]);im=n.convert('RGB')
        sheet.paste(im,(k%8*256,k//8*280+24));dr.text((k%8*256+6,k//8*280+3),f'R{i:03d}',font=FONT,fill='white')
        previews.append(im.resize((768,768),Image.Resampling.NEAREST))
    sheet.save(d/'native_contact_sheet.png')
    previews[0].save(d/'native_preview.gif',save_all=True,append_images=previews[1:],duration=83,loop=0)
    native_dir=d/'native_review';native_dir.mkdir(exist_ok=True)
    for i,im in enumerate(native):im.save(native_dir/f'R{i:03d}.png')
    verified=[]
    for path,count,fps in [(d/'generated.mp4',39,24),(d/'reference_vs_generated.mp4',39,24),(d/'reference_vs_generated_half_speed.mp4',39,12)]:
        with av.open(str(path)) as c:
            s=c.streams.video[0];decoded=list(c.decode(s));assert len(decoded)==count and float(s.average_rate)==fps
            verified.append({'path':path.name,'frames':len(decoded),'fps':fps,'size':[s.width,s.height]})
    report={'status':'generated_pending_visual_review','variant':variant,'control_kind':control_kind,'source_frames':39,'fps':24,'metrics':metrics,'videos_verified':verified,
            'comparison_fixed_crop':crop,'review_focus':['R000-R004 pose melting','hand inside belly / stretched arm','rigid sword shape and trajectory','hornless head, tail and body consistency','R013-R038 unanchored motion'],
            'native_review_pipeline':'Existing key_green/drop_fx/keep_body/to_native/denoise/outline, origin0 scale3; review only, no asset import. Raw contact sheet and comparison retain model artifacts.',
            'native_review_fps':12,'native_preview_source_indices':list(range(0,39,2))}
    (d/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'variant':variant,'video_checks':verified,'opaque_range':[min(x['native_opaque_pixels'] for x in metrics),max(x['native_opaque_pixels'] for x in metrics)]},ensure_ascii=False,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('variant',choices=['original','proxy']);ap.add_argument('--attempt',type=int,default=1);ap.add_argument('--control',choices=['depth','lineart'],default='depth');args=ap.parse_args();run(args.variant,args.attempt,args.control)
