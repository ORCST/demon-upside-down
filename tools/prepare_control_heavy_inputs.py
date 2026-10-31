"""Prepare green reference inputs and verify the rendered control delivery.

No ComfyUI calls, model changes or game asset imports are performed.
Run after export_control_heavy_combo.py and render_control_heavy_combo.py.
"""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import av
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser()
ap.add_argument('--output',default='art_source/control/heavy_combo_v01')
ap.add_argument('--first-trial',action='store_true',help='Only K4 and K6 intermediate guides; keep K2 for later trials')
args=ap.parse_args()
OUT=(ROOT/args.output).resolve()
if not OUT.is_relative_to(ROOT):raise ValueError('Output must stay inside project')
META=json.loads((OUT/'render_manifest.json').read_text(encoding='utf-8'))
N=META['frame_count']
POSES=ROOT/'art_source/reference/poses/heavy_combo_v02'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    folder=OUT/'inputs';folder.mkdir(exist_ok=True)
    anchors=[]
    selected=[(0,'idle_tail'),(8,'hc1_k4'),(12,'hc1_k6')] if args.first_trial else [(0,'idle_tail'),(5,'hc1_k2'),(8,'hc1_k4'),(12,'hc1_k6')]
    for f,pose in selected:
        source=POSES/f'niulai_{pose}_native.png'
        if f==0:source=ROOT/'art_source/reference/poses/niulai_idle_tail_native.png'
        native=Image.open(source).convert('RGBA')
        assert native.size==(256,256)
        im=native.resize((768,768),Image.Resampling.NEAREST)
        green=Image.new('RGBA',(768,768),(0,255,0,255));green.alpha_composite(im)
        target=folder/f'R{f:03d}_{pose}_green.png';green.convert('RGB').save(target)
        actual=np.asarray(Image.open(target));expected=np.asarray(native)
        expected=expected[:,:,:3]* (expected[:,:,3:4]//255) + np.array([0,255,0],np.uint8)*(1-expected[:,:,3:4]//255)
        assert np.array_equal(actual,np.repeat(np.repeat(expected,3,axis=0),3,axis=1))
        anchors.append({'frame_index':f,'time_seconds':f/24,'pose':pose,'role':'first_frame' if f==0 else 'optional_intermediate_guide',
                        'source':source.relative_to(ROOT).as_posix(),'input':target.relative_to(OUT).as_posix(),
                        'offset_native_px':[0,0],'source_sha256':digest(source),'input_sha256':digest(target)})
    inputs={'fps':24,'size':[768,768],'control_frames':N,'anchors':anchors,
            'status':'prepared_only_not_submitted','node_support':'Intermediate guide support must be checked after the approved ComfyUI upgrade.',
            'temporal_note':'Masters are exactly R000-R023. The installed H3 node snaps length up to 17k+5 (24 -> 39). Resolve trimming/padding explicitly before generation; no duplicated frames or retiming are baked into these controls.'}
    if N%17==5:inputs['temporal_note']=f'R000-R{N-1:03d}, {N} source-speed frames at 24fps, already on the H3 17k+5 grid; no padded/duplicated frames or retiming.'
    if args.first_trial:inputs['first_trial_note']='Use only K4@R008 and K6@R012 as intermediate anchors. K2 is intentionally excluded. Native node index-to-latent mapping still needs verification.'
    (OUT/'anchor_manifest.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2),encoding='utf-8')
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    sheet=Image.new('RGB',(len(anchors)*384,3*408),'#171c26');draw=ImageDraw.Draw(sheet)
    for col,a in enumerate(anchors):
        f=a['frame_index']
        for row,variant in enumerate(['original','proxy','anchor']):
            path=OUT/a['input'] if variant=='anchor' else OUT/variant/'beauty'/f'R{f:03d}.png'
            im=Image.open(path).convert('RGB').resize((384,384),Image.Resampling.NEAREST if row==2 else Image.Resampling.LANCZOS)
            sheet.paste(im,(col*384,row*408+24))
            draw.text((col*384+8,row*408+2),f"R{f:03d} / {variant} / {a['pose']}",font=font,fill='white')
    sheet.save(OUT/'anchor_alignment.png')

    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'checks':{},'videos':[],'variants':{},'warnings':[
        'Devin accepted the v01 starting pose without an initial transition. Check generated R000-R004 for melting and hands intersecting the belly.',
        'Proxy is a modified humanoid, not an exact NiuLai model; appearance fidelity is untested.',
        f'R018-R{N-1:03d} continue the next action, not a new independent recovery.',
        inputs['temporal_note'],
        'No AI generation, ComfyUI upgrade, model download or in-game validation performed.'
    ]}
    modes=['beauty','depth','depth16','lineart','mask','sword_mask'];png_count=0
    for variant in ['original','proxy']:
        rows=[m for m in META['frame_metrics'] if m['variant']==variant]
        assert len(rows)==N
        assert all(m['body_bbox'][3]==623 for m in rows)
        assert all(m['sword_visible_pixels']>0 for m in rows)
        min_margin=768
        for f in META['frames']:
            for mode in modes:
                path=OUT/variant/mode/f'R{f:03d}.png';im=Image.open(path);im.load()
                assert im.size==(768,768),(variant,f,mode)
                arr=np.asarray(im)
                if mode in ['lineart','mask','sword_mask']:assert set(np.unique(arr))<={0,255}
                if mode=='depth16':assert arr.max()>255 and arr.max()<=65535
                png_count+=1
            cache=np.load(OUT/variant/'cache'/f'R{f:03d}.npz');valid=np.isfinite(cache['z'])
            mask=np.asarray(Image.open(OUT/variant/'mask'/f'R{f:03d}.png'))>0
            assert np.array_equal(mask,valid)
            depth=np.asarray(Image.open(OUT/variant/'depth'/f'R{f:03d}.png'))
            expected=np.zeros((768,768),np.uint8)
            expected[valid]=np.rint(np.clip((META['depth_far']-cache['z'][valid])/(META['depth_far']-META['depth_near']),0,1)*255).astype(np.uint8)
            assert np.array_equal(depth,expected)
            geo=np.load(OUT/variant/'geometry'/f'R{f:03d}.npz');v=geo['vertices']
            assert np.isfinite(v).all()
            assert (v[:,:2]>=0).all() and (v[:,:2]<768).all(),('Geometry clipped',variant,f)
            margin=float(min(v[:,0].min(),v[:,1].min(),767-v[:,0].max(),767-v[:,1].max()));min_margin=min(min_margin,margin)
        corrections=[c['screen_y_translation_px'] for c in META['variants'][variant]['ground_corrections'].values()]
        report['variants'][variant]={'frames':N,'pngs':N*len(modes),'frame0_body_height_px':192,
            'feet_last_row_range':[min(m['body_bbox'][3] for m in rows),max(m['body_bbox'][3] for m in rows)],
            'minimum_geometry_margin_px':round(min_margin,3),
            'ground_translation_range_px':[min(corrections),max(corrections)],
            'sword_visible_pixel_range':[min(m['sword_visible_pixels'] for m in rows),max(m['sword_visible_pixels'] for m in rows)]}
    videos=[OUT/v/f'{mode}.mp4' for v in ['original','proxy'] for mode in ['beauty','depth','lineart']]+[OUT/'control_compare.mp4']
    for path in videos:
        with av.open(str(path)) as c:
            s=c.streams.video[0];frames=list(c.decode(s))
            assert len(frames)==N and s.average_rate==24
            times=[float(f.pts*f.time_base) for f in frames]
            assert np.allclose(times,np.arange(N)/24,atol=1e-5)
            size=[s.width,s.height]
            assert size==([1152,640] if path.name=='control_compare.mp4' else [768,768])
            report['videos'].append({'path':path.relative_to(OUT).as_posix(),'decoded_frames':len(frames),'fps':float(s.average_rate),'size':size,'duration_seconds':N/24,'sha256':digest(path)})
    files=[ROOT/'tools/export_control_heavy_combo.py',ROOT/'tools/render_control_heavy_combo.py',Path(__file__),ROOT/META['source_blend']]
    report['provenance']={p.relative_to(ROOT).as_posix():digest(p) for p in files}
    report['checks']={'control_pngs':png_count,'all_dimensions_correct':True,'finite_geometry_inside_canvas':True,'both_variants_grounded':True,
        'depth_matches_global_z_buffer':True,'binary_masks_and_lineart':True,'sword_has_visible_pixels_every_frame':True,
        'all_7_videos_decode_expected_frames_at_24fps':True,'green_inputs_exact_nearest_neighbor':True}
    report['status']='technical_checks_passed'
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'control_pngs':png_count,'green_inputs':len(anchors),'videos':len(videos),'variants':report['variants']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
