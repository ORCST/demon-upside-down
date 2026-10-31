"""Local H3 fl2va experiment; motion described from Heavy Combo, NOT video-conditioned."""
import json,time,urllib.parse
from pathlib import Path
from PIL import Image
from comfy_minimax import api,upload,build_graph,frame_count

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'art_source/minimax/heavy_combo_trial_v01'
OUT.mkdir(parents=True,exist_ok=True)
if (OUT/'job.json').exists():
    raise SystemExit('Existing job retained; choose a new trial directory before rerunning.')
ref=ROOT/'art_source/reference/poses/niulai_idle_tail_native.png'
im=Image.open(ref).convert('RGBA').resize((768,768),Image.Resampling.NEAREST)
canvas=Image.new('RGBA',im.size,(0,255,0,255));canvas.alpha_composite(im)
first=OUT/'niulai_first.png';canvas.convert('RGB').save(first)
prompt=('2D pixel art side-scrolling action game animation. The same small yellow calf warrior '
        'with brown shorts, brown boots, a short tail and a large solid gray greatsword as the supplied image. '
        'One continuous heavy sword combo facing screen right: briefly bend the knees and pull the sword back; '
        'step forward with the right foot and sweep the sword upward with a strong torso twist; '
        'continue the momentum into a broad powerful horizontal slash in front of the body; '
        'raise the sword and deliver a final heavy downward cleave, leaning the torso forward with bent knees, '
        'then recover to the original ready stance. The sword has a single rigid straight blade, '
        'its handle firmly held in the right hand; the other arm balances the body during the broad swings. '
        'Clear anticipation, fast decisive cuts, visible weight and follow-through. '
        'The calf remains in right-facing side profile, entirely inside the frame, with consistent body size. '
        'Locked orthographic side camera, constant framing, crisp pixel shapes and the original limited palette. '
        'A uniform solid pure green background fills the entire frame throughout. Only the calf and his solid sword animate.')
(OUT/'prompt.txt').write_text(prompt,encoding='utf-8')
host='127.0.0.1:8189'
for _ in range(60):
    try:api(host,'/system_stats');break
    except OSError:time.sleep(3)
else:raise SystemExit('Local ComfyUI did not start.')
name=upload(host,first)
graph=build_graph(prompt,768,768,frame_count(4.33),20261015,'heavy_combo_trial_v01',name,name,8)
(OUT/'workflow_api.json').write_text(json.dumps(graph,indent=2),encoding='utf-8')
reply=json.loads(api(host,'/prompt',json.dumps({'prompt':graph}).encode(),{'Content-Type':'application/json'}))
job={'prompt_id':reply['prompt_id'],'mode':'fl2va_first_last_frame_motion_prompt_approximation','reference_motion':'Sword_Heavy_Combo','reference_video_fed_to_model':False,'seed':20261015,'fps':24,'requested_frames':frame_count(4.33),'size':[768,768],'steps':8}
(OUT/'job.json').write_text(json.dumps(job,indent=2),encoding='utf-8')
print('QUEUED',reply['prompt_id'],flush=True)
start=time.time()
while True:
    hist=json.loads(api(host,'/history/'+reply['prompt_id']))
    if reply['prompt_id'] in hist:
        entry=hist[reply['prompt_id']]
        (OUT/'history.json').write_text(json.dumps(entry,indent=2),encoding='utf-8')
        if entry.get('status',{}).get('status_str')=='error':raise SystemExit('Generation failed; see history.json')
        break
    time.sleep(5)
frames=OUT/'frames';frames.mkdir(exist_ok=True);n=0
for node in entry['outputs'].values():
    for kind in ('images','videos','gifs'):
        for f in node.get(kind,[]):
            q=urllib.parse.urlencode({k:f[k] for k in ('filename','subfolder','type')})
            data=api(host,'/view?'+q)
            if f['filename'].lower().endswith('.png'):
                n+=1;(frames/f'{n:04d}.png').write_bytes(data)
            else:(OUT/('generated'+Path(f['filename']).suffix)).write_bytes(data)
job.update(elapsed_seconds=round(time.time()-start,2),saved_frames=n,status='generated_pending_visual_review')
(OUT/'job.json').write_text(json.dumps(job,indent=2),encoding='utf-8')
print('DONE',n,job['elapsed_seconds'],flush=True)
