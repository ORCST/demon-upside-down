"""CPU orthographic z-buffer rendering of Blender-evaluated single-actor geometry."""
import argparse,json
from pathlib import Path
import av,cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser()
ap.add_argument('--output',default='art_source/control/heavy_combo_v01')
args=ap.parse_args()
OUT=(ROOT/args.output).resolve()
if not OUT.is_relative_to(ROOT):raise ValueError('Output must stay inside project')
META=json.loads((OUT/'render_manifest.json').read_text(encoding='utf-8'))
W=H=768
COLORS=np.array([[190,197,210],[80,169,192],[62,75,88],[114,85,59]],np.float32)

def render(vertices,triangles,materials):
    z=np.full((H,W),np.inf,np.float32);owner=np.full((H,W),255,np.uint8)
    rgb=np.zeros((H,W,3),np.uint8)
    # Smooth area-weighted vertex normals, shaded just for diagnostic beauty.
    normals=np.zeros_like(vertices)
    cross=np.cross(vertices[triangles[:,1]]-vertices[triangles[:,0]],vertices[triangles[:,2]]-vertices[triangles[:,0]])
    for j in range(3):np.add.at(normals,triangles[:,j],cross)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-8)
    light=np.array([-.3,-.6,-.75]);light/=np.linalg.norm(light)
    intensities=.35+.65*np.abs(normals@light)
    for ids,mat in zip(triangles,materials):
        v=vertices[ids]
        x0=max(0,int(np.floor(v[:,0].min())));x1=min(W-1,int(np.ceil(v[:,0].max())))
        y0=max(0,int(np.floor(v[:,1].min())));y1=min(H-1,int(np.ceil(v[:,1].max())))
        if x1<x0 or y1<y0:continue
        ax,ay,az=v[0];bx,by,bz=v[1];cx,cy,cz=v[2]
        den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(den)<1e-7:continue
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1];xx=xx+.5;yy=yy+.5
        wa=((by-cy)*(xx-cx)+(cx-bx)*(yy-cy))/den
        wb=((cy-ay)*(xx-cx)+(ax-cx)*(yy-cy))/den;wc=1-wa-wb
        depth=wa*az+wb*bz+wc*cz
        region=z[y0:y1+1,x0:x1+1]
        win=(wa>=-1e-5)&(wb>=-1e-5)&(wc>=-1e-5)&(depth<region)
        if not win.any():continue
        region[win]=depth[win]
        owner[y0:y1+1,x0:x1+1][win]=mat
        intensity=wa*intensities[ids[0]]+wb*intensities[ids[1]]+wc*intensities[ids[2]]
        color=np.clip(intensity[...,None]*COLORS[mat],0,255).astype(np.uint8)
        rgb[y0:y1+1,x0:x1+1][win]=color[win]
    return z,owner,rgb

def encode(path,frames,fps=24):
    c=av.open(str(path),'w',options={'movflags':'+faststart'});s=c.add_stream('libx264',rate=fps)
    s.width,s.height=frames[0].size;s.pix_fmt='yuv420p';s.options={'crf':'16','preset':'fast'}
    for i,im in enumerate(frames):
        f=av.VideoFrame.from_image(im.convert('RGB'));f.pts=i
        for p in s.encode(f):c.mux(p)
    for p in s.encode():c.mux(p)
    c.close()

def main():
    caches=[];near=np.inf;far=-np.inf;union=[W,H,0,0];metrics=[]
    for variant in ['original','proxy']:
        folder=OUT/variant
        for name in ['depth','depth16','lineart','beauty','mask','sword_mask','cache']:(folder/name).mkdir(exist_ok=True)
        for f in META['frames']:
            src=np.load(folder/'geometry'/f'R{f:03d}.npz')
            z,owner,color=render(src['vertices'],src['triangles'],src['materials'])
            valid=np.isfinite(z);y,x=np.where(valid)
            assert x.size,('Empty render',variant,f)
            near=min(near,float(z[valid].min()));far=max(far,float(z[valid].max()))
            union=[min(union[0],int(x.min())),min(union[1],int(y.min())),max(union[2],int(x.max())),max(union[3],int(y.max()))]
            np.savez_compressed(folder/'cache'/f'R{f:03d}.npz',z=z,owner=owner)
            beauty=np.where(valid[...,None],color,np.array([45,51,63],np.uint8))
            Image.fromarray(beauty.astype(np.uint8)).save(folder/'beauty'/f'R{f:03d}.png')
            Image.fromarray(valid.astype(np.uint8)*255).save(folder/'mask'/f'R{f:03d}.png')
            Image.fromarray(((owner>0)&(owner<255)).astype(np.uint8)*255).save(folder/'sword_mask'/f'R{f:03d}.png')
            body=owner==0;by,bx=np.where(body)
            metrics.append({'variant':variant,'frame':f,'bbox':[int(x.min()),int(y.min()),int(x.max()),int(y.max())],'body_bbox':[int(bx.min()),int(by.min()),int(bx.max()),int(by.max())],'body_pixels':int(body.sum()),'sword_visible_pixels':int(((owner>0)&(owner<255)).sum())})
            caches.append((variant,f));print('RASTER',variant,f,flush=True)
    padding=max(1.,(far-near)*.05);near-=padding;far+=padding
    crop=[max(0,union[0]-24),max(0,union[1]-24),min(W,union[2]+25),min(H,union[3]+25)]
    for variant,f in caches:
        folder=OUT/variant;c=np.load(folder/'cache'/f'R{f:03d}.npz');z=c['z'];valid=np.isfinite(z)
        normalized=np.zeros((H,W),np.float32);normalized[valid]=np.clip((far-z[valid])/(far-near),0,1)
        d=(normalized*255).round().astype(np.uint8)
        Image.fromarray(d).save(folder/'depth'/f'R{f:03d}.png')
        Image.fromarray((normalized*65535).round().astype(np.uint16)).save(folder/'depth16'/f'R{f:03d}.png')
        edges=cv2.Canny(d,25,60)|cv2.Canny(valid.astype(np.uint8)*255,50,100)
        Image.fromarray(edges).save(folder/'lineart'/f'R{f:03d}.png')
    for variant in ['original','proxy']:
        for mode in ['beauty','depth','lineart']:
            frames=[Image.open(OUT/variant/mode/f'R{f:03d}.png').convert('RGB') for f in META['frames']]
            encode(OUT/variant/(mode+'.mp4'),frames)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
    preview=[]
    for f in META['frames']:
        board=Image.new('RGB',(1152,640),'#171c26');draw=ImageDraw.Draw(board)
        for row,variant in enumerate(['original','proxy']):
            for col,mode in enumerate(['beauty','depth','lineart']):
                im=Image.open(OUT/variant/mode/f'R{f:03d}.png').convert('RGB').crop(crop)
                im.thumbnail((384,270),Image.Resampling.LANCZOS)
                x=col*384+(384-im.width)//2;y=row*320+40
                board.paste(im,(x,y));draw.text((col*384+12,row*320+10),('原比例' if row==0 else '比例代理')+' / '+mode+f' / R{f:03d}',font=font,fill='white')
        preview.append(board)
    encode(OUT/'control_compare.mp4',preview)
    samples=[0,8,12,23,30,38] if META['frame_count']==39 else [0,3,8,10,12,17]
    sheet=Image.new('RGB',(1536,2*256),'#171c26');draw=ImageDraw.Draw(sheet)
    for row,variant in enumerate(['original','proxy']):
        for col,f in enumerate(samples):
            im=Image.open(OUT/variant/'beauty'/f'R{f:03d}.png').crop(crop);im.thumbnail((256,220),Image.Resampling.LANCZOS)
            sheet.paste(im,(col*256+(256-im.width)//2,row*256+34));draw.text((col*256+8,row*256+6),variant+f' R{f:03d}',font=font,fill='white')
    sheet.save(OUT/'control_contact_sheet.png')
    # Frame0 overlay exposes, rather than hides, the remaining pose mismatch.
    ref=Image.open(ROOT/'art_source/reference/poses/niulai_idle_tail_native.png').convert('RGBA').resize((768,768),Image.Resampling.NEAREST)
    overlay=Image.new('RGB',(1536,768));od=ImageDraw.Draw(overlay)
    for i,variant in enumerate(['original','proxy']):
        im=Image.open(OUT/variant/'beauty/R000.png').convert('RGBA');r=ref.copy();r.putalpha(r.getchannel('A').point(lambda a:round(a*.50)));im.alpha_composite(r)
        overlay.paste(im.convert('RGB'),(i*768,0));od.text((i*768+18,18),variant+' / R000 + 牛来半透明',font=font,fill='white')
        od.line((i*768,624,i*768+767,624),fill='#56b9a8',width=1);od.line((i*768+336,32,i*768+336,740),fill='#a590bd',width=1)
    overlay.save(OUT/'frame0_alignment.png')
    META.update(depth_near=near,depth_far=far,preview_common_crop=crop,renderer='CPU triangle z-buffer using Blender-evaluated vertices; exact orthographic projection',frame_metrics=metrics)
    (OUT/'render_manifest.json').write_text(json.dumps(META,ensure_ascii=False,indent=2),encoding='utf-8')
    print('CONTROL_RENDER_DONE',flush=True)

if __name__=='__main__':main()
