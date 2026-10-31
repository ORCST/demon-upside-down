"""Combine the three completed first-round trials and their audit summaries."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from prep_sprites import key_green
from review_h3_control_heavy import encode

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'art_source/minimax/heavy_combo_ctrl_v01'
CONTROL=ROOT/'art_source/control/heavy_combo_v02_39f'
TRIALS=[('depth_original_attempt02','成人比例 depth'),('depth_proxy','比例代理 depth'),('lineart_proxy','比例代理 Canny')]

def main():
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    m=json.loads((CONTROL/'render_manifest.json').read_text(encoding='utf8'));crop=m['preview_common_crop'][:]
    frames={}
    for name,_ in TRIALS:
        frames[name]=[Image.open(OUT/name/'frames'/f'R{i:03d}.png').convert('RGB') for i in range(39)]
        for im in frames[name]:
            y,x=np.where(key_green(np.asarray(im))>.5)
            if x.size:crop=[max(0,min(crop[0],int(x.min())-12)),max(0,min(crop[1],int(y.min())-12)),min(768,max(crop[2],int(x.max())+13)),min(768,max(crop[3],int(y.max())+13))]
    preview=[]
    for i in range(39):
        b=Image.new('RGB',(1536,340),'#171c26');draw=ImageDraw.Draw(b)
        items=[(Image.open(CONTROL/'proxy/beauty'/f'R{i:03d}.png').convert('RGB'),'代理白模参考')]+[(frames[n][i],label) for n,label in TRIALS]
        for col,(im,label) in enumerate(items):
            p=im.crop(crop);p.thumbnail((384,308),Image.Resampling.LANCZOS)
            b.paste(p,(col*384+(384-p.width)//2,30));draw.text((col*384+8,5),f'{label} / R{i:03d}',font=font,fill='white')
        preview.append(b)
    encode(OUT/'trial_compare.mp4',preview,24)
    encode(OUT/'trial_compare_half_speed.mp4',preview,12)
    chosen=[0,3,8,10,12,16,24,38]
    sheet=Image.new('RGB',(1536,len(chosen)*340),'#171c26')
    for k,i in enumerate(chosen):sheet.paste(preview[i],(0,k*340))
    sheet.save(OUT/'trial_compare_keyframes.png')
    results=[]
    for name,label in TRIALS:
        folder=OUT/name;job=json.loads((folder/'job.json').read_text(encoding='utf8'));review=json.loads((folder/'review.json').read_text(encoding='utf8'));history=json.loads((folder/'history.json').read_text(encoding='utf8'))
        messages=history['status'].get('messages',[])
        ts={kind:payload.get('timestamp') for kind,payload in messages if isinstance(payload,dict) and payload.get('timestamp')}
        start=ts.get('execution_start');end=ts.get('execution_success')
        sec=(end-start)/1000 if start and end else None
        results.append({'directory':name,'label':label,'prompt_id':job['prompt_id'],'frames':39,'fps':24,'execution_seconds':sec,'manual_verdict':review.get('manual_verdict','pending'),
                        'native_opaque_px_range':[min(x['native_opaque_pixels'] for x in review['metrics']),max(x['native_opaque_pixels'] for x in review['metrics'])],
                        'source_hashes':job['source_sha256'],'generated_video_sha256':hashlib.sha256((folder/'generated.mp4').read_bytes()).hexdigest()})
    result={'status':'first_round_completed_no_game_import','best_body_preservation_in_this_trial':'depth_proxy','all_generated_trials_require_art_revision':True,
            'trials':results,'failed_attempt':'depth_original (native compiler abort, no frames)','comparison_fixed_crop':crop,
            'comparison_video_fps':24,'slower_review_copy_fps':12,'notes':['Single seed per condition: this is a feasibility comparison, not a general benchmark.','Each reference_vs_generated video uses its matching mannequin proportion; the first panel of this combined overview is the proxy reference.','Pixel cleanup is diagnostic and cannot turn missing or smeared sword shapes into usable art.']}
    (OUT/'trial_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'trials':[{k:r[k] for k in ['directory','execution_seconds','manual_verdict','native_opaque_px_range']} for r in results],'crop':crop},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
