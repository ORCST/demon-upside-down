"""First H3 control trial: real depth video + idle image + K4/K6 guides.

Each variant owns one job.json. An existing job is never submitted again.
Use --collect to resume reading an already submitted job without requeueing.
"""
import argparse,hashlib,json,mimetypes,time,urllib.parse,uuid
from pathlib import Path
from comfy_minimax import api,build_graph

ROOT=Path(__file__).resolve().parent.parent
CONTROL=ROOT/'art_source/control/heavy_combo_v02_39f'
OUT=ROOT/'art_source/minimax/heavy_combo_ctrl_v01'
PATCH='minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors'
SEED=20261015
PROMPT=(
    '2D pixel art side-scrolling action game animation of the small yellow calf warrior in the supplied images. '
    'The calf has a rounded hornless yellow head, cream muzzle, a thick dark eyebrow, a deadpan eye, pink inner ears, '
    'brown shorts, brown hooves, and a short tail with a dark tuft. Keep the same compact body and limited pixel palette. '
    'One large rigid straight steel-gray greatsword keeps the same blade shape and size throughout the animation. '
    'Follow the supplied control motion: lower into a crouch with the sword behind the body, sweep the sword forward, '
    'then raise it and continue into the next heavy swing. The hand stays firmly attached to the sword grip. '
    'The supplied key poses fix the calf appearance at their corresponding times. '
    'Locked orthographic side camera, right-facing character, constant framing, full body and sword inside the canvas. '
    'Crisp pixel shapes on a uniform solid pure green background throughout.'
)

def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def upload_file(host,path,name):
    boundary=uuid.uuid4().hex
    mime=mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n').encode()+path.read_bytes()+(f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{boundary}--\r\n').encode()
    return json.loads(api(host,'/upload/image',body,{'Content-Type':f'multipart/form-data; boundary={boundary}'}))['name']

def graph_for(host,variant,control_kind='depth'):
    first=upload_file(host,CONTROL/'inputs/R000_idle_tail_green.png','hc_ctrl_idle_green.png')
    k4=upload_file(host,CONTROL/'inputs/R008_hc1_k4_green.png','hc_ctrl_R008_k4_green.png')
    k6=upload_file(host,CONTROL/'inputs/R012_hc1_k6_green.png','hc_ctrl_R012_k6_green.png')
    control=upload_file(host,CONTROL/variant/(control_kind+'.mp4'),f'hc_ctrl_39f_{variant}_{control_kind}.mp4')
    g=build_graph(PROMPT,768,768,39,SEED,'heavy_combo_control/'+variant+'_'+control_kind,first,None,8)
    # Audio is still part of H3 sampling, but the action reference export is silent.
    del g['14'];g['15']['inputs'].pop('audio')
    g.update({
        '22':{'class_type':'ModelPatchLoader','inputs':{'name':PATCH}},
        '23':{'class_type':'LoadVideo','inputs':{'file':control}},
        '24':{'class_type':'GetVideoComponents','inputs':{'video':['23',0]}},
        '25':{'class_type':'MiniMaxH3FunControlNetApply','inputs':{'model':['2',0],'model_patch':['22',0],
            'vae':['4',0],'strength':1.0,'start_percent':0.0,'end_percent':1.0,'control_video':['24',0]}},
        '30':{'class_type':'LoadImage','inputs':{'image':k4}},
        '31':{'class_type':'MiniMaxH3AddGuide','inputs':{'positive':['7',0],'latent':['7',1],'vae':['4',0],'image':['30',0],'frame_idx':8}},
        '32':{'class_type':'LoadImage','inputs':{'image':k6}},
        '33':{'class_type':'MiniMaxH3AddGuide','inputs':{'positive':['31',0],'latent':['7',1],'vae':['4',0],'image':['32',0],'frame_idx':12}},
    })
    g['10']['inputs']['model']=['25',0];g['11']['inputs']['model']=['25',0]
    g['11']['inputs']['conditioning']=['33',0]
    return g

def collect(host,d,job):
    pid=job.get('prompt_id')
    if not pid:raise RuntimeError('Job has no confirmed prompt_id; do not requeue automatically')
    started=time.monotonic();last=0
    while True:
        try:hist=json.loads(api(host,'/history/'+pid))
        except OSError:
            job['status']='server_unreachable_during_execution';write(d/'job.json',job);raise
        if pid in hist:
            entry=hist[pid];break
        if time.monotonic()-last>=30:
            queue=json.loads(api(host,'/queue'))
            print('WAIT',d.name,'seconds',round(time.monotonic()-started),'running',len(queue.get('queue_running',[])),flush=True);last=time.monotonic()
        time.sleep(5)
    write(d/'history.json',entry)
    if entry.get('status',{}).get('status_str')!='success':
        job['status']='failed';write(d/'job.json',job)
        raise RuntimeError('Comfy execution failed; see history.json (not resubmitted)')
    fr=d/'frames';fr.mkdir(exist_ok=True);n=0
    for node in entry['outputs'].values():
        for kind in ('images','videos','gifs'):
            for item in node.get(kind,[]):
                if item.get('type')!='output':continue
                q=urllib.parse.urlencode({k:item[k] for k in ('filename','subfolder','type')})
                data=api(host,'/view?'+q)
                if item['filename'].lower().endswith('.png'):
                    (fr/f'R{n:03d}.png').write_bytes(data);n+=1
                else:(d/('generated'+Path(item['filename']).suffix)).write_bytes(data)
    if n!=39:raise RuntimeError(f'Expected 39 saved frames, got {n}; inspect outputs before retrying collection')
    job.update(status='generated_pending_visual_review',saved_frames=n,collected_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    write(d/'job.json',job);print('GENERATED',d.name,n,flush=True)

def run(host,variant,collect_only,attempt=1,control_kind='depth'):
    d=OUT/(control_kind+'_'+variant+(f'_attempt{attempt:02d}' if attempt>1 else ''));d.mkdir(parents=True,exist_ok=True)
    jobfile=d/'job.json'
    if jobfile.exists():
        if collect_only:collect(host,d,json.loads(jobfile.read_text(encoding='utf8')))
        else:print('SKIP',variant,'job.json exists; never requeue',flush=True)
        return
    if collect_only:raise RuntimeError('No existing job to collect')
    schemas=json.loads(api(host,'/object_info'))
    required=['MiniMaxH3FunControlNetApply','MiniMaxH3AddGuide','ModelPatchLoader','LoadVideo','GetVideoComponents']
    for name in required:
        if name not in schemas:raise RuntimeError('Missing native node '+name)
    write(d/'node_schemas.json',{k:schemas[k] for k in required})
    g=graph_for(host,variant,control_kind)
    if attempt>1:
        for key in ['16','17']:g[key]['inputs']['filename_prefix']+=f'_attempt{attempt:02d}'
    for node in g.values():
        for name in schemas[node['class_type']]['input'].get('required',{}):
            if name not in node['inputs']:raise RuntimeError(f"Missing required input {node['class_type']}.{name}")
    (d/'prompt.txt').write_text(PROMPT,encoding='utf8');write(d/'workflow_api.json',g)
    sources=[CONTROL/variant/(control_kind+'.mp4'),CONTROL/'render_manifest.json',CONTROL/'inputs/R000_idle_tail_green.png',CONTROL/'inputs/R008_hc1_k4_green.png',CONTROL/'inputs/R012_hc1_k6_green.png',Path(__file__)]
    job={'status':'submission_prepared','mode':'fl2va_plus_native_fun_controlnet_and_pixel_frame_guides','variant':variant,'attempt':attempt,'control_kind':control_kind,
         'seed':SEED,'steps':8,'fps':24,'frames':39,'size':[768,768],'strength':1.0,'anchors':{'8':'hc1_k4','12':'hc1_k6'},
         'K2_included':False,'control_video_fed_to_model':True,'control_frames_padded':False,
         'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sources},
         'submitted_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    job['system_stats']=json.loads(api(host,'/system_stats'))
    write(jobfile,job)
    try:
        response=json.loads(api(host,'/prompt',json.dumps({'prompt':g,'client_id':str(uuid.uuid4())}).encode(),{'Content-Type':'application/json'}))
    except Exception:
        job['status']='submission_unconfirmed_do_not_requeue';write(jobfile,job);raise
    job.update(prompt_id=response['prompt_id'],status='queued');write(jobfile,job)
    print('QUEUED',variant,job['prompt_id'],flush=True);collect(host,d,job)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('variant',choices=['original','proxy']);ap.add_argument('--host',default='127.0.0.1:8189');ap.add_argument('--collect',action='store_true');ap.add_argument('--attempt',type=int,default=1);ap.add_argument('--control',choices=['depth','lineart'],default='depth')
    args=ap.parse_args();run(args.host,args.variant,args.collect,args.attempt,args.control)
