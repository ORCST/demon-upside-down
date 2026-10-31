"""Download only the user-approved H3 ControlNet patch; verify official LFS hash."""
import argparse,hashlib,json,struct,time,urllib.request,urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
AUDIT=ROOT/'outputs/h3_control_setup_20261015'
NAME='minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors'
DEST=Path('D:/Comfy-Desktop/ComfyUI-Shared/models/model_patches')/NAME
URL='https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/model_patches/'+NAME

def checksum(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def parallel_download(partial,size,expected):
    checkpoint=DEST.with_suffix(DEST.suffix+'.ranges.json')
    if checkpoint.exists():ranges=json.loads(checkpoint.read_text())
    else:
        prefix=partial.stat().st_size if partial.exists() else 0
        stride=(size-prefix+3)//4
        ranges={'prefix':prefix,'parts':[[i,start,min(size-1,start+stride-1)] for i,start in enumerate(range(prefix,size,stride))]}
        checkpoint.write_text(json.dumps(ranges),encoding='utf8')
    def fetch(spec):
        i,start,end=spec;part=DEST.with_suffix(DEST.suffix+f'.part{i}')
        for attempt in range(3):
            have=part.stat().st_size if part.exists() else 0
            if have==end-start+1:return part
            if have>end-start+1:raise RuntimeError('Range part too large')
            begin=start+have
            try:
                req=urllib.request.Request(URL,headers={'User-Agent':'niulai-local-setup','Range':f'bytes={begin}-{end}'})
                with urllib.request.urlopen(req,timeout=60) as r:
                    if r.status!=206 or not r.headers.get('Content-Range','').startswith(f'bytes {begin}-'):raise RuntimeError('Server did not honor range')
                    with part.open('ab') as f:
                        last=time.monotonic()
                        while chunk:=r.read(4*1024*1024):
                            f.write(chunk);have+=len(chunk)
                            if have>end-start+1:raise RuntimeError('Range response too large')
                            if time.monotonic()-last>=10:
                                done=ranges['prefix']+sum(p.stat().st_size for p in DEST.parent.glob(NAME+'.part[0-3]'))
                                print(f'PARALLEL_DOWNLOAD {done}/{size} {done/size:.1%}',flush=True);last=time.monotonic()
                if have==end-start+1:return part
            except (urllib.error.URLError,TimeoutError,OSError) as e:
                print('RANGE_RETRY',i,attempt+1,type(e).__name__,getattr(e,'code',''),flush=True)
        raise RuntimeError('Incomplete range; checkpoint preserved')
    with ThreadPoolExecutor(max_workers=4) as pool:parts=list(pool.map(fetch,ranges['parts']))
    assembled=DEST.with_suffix(DEST.suffix+'.assembling')
    with assembled.open('wb') as out:
        for path in ([partial] if ranges['prefix'] else [])+parts:
            with path.open('rb') as f:
                for chunk in iter(lambda:f.read(8*1024*1024),b''):out.write(chunk)
    if assembled.stat().st_size!=size or checksum(assembled)!=expected:raise RuntimeError('Assembled SHA256 mismatch; files preserved')
    assembled.rename(DEST)
    for path in ([partial] if ranges['prefix'] else [])+parts+[checkpoint]:path.unlink()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--parallel',action='store_true');args=ap.parse_args()
    metadata=json.loads((AUDIT/'patches_source.json').read_text(encoding='utf8'))
    item=next(x for x in metadata if x['path']=='model_patches/'+NAME)
    size=item['size'];expected=item['lfs']['oid']
    DEST.parent.mkdir(parents=True,exist_ok=True)
    partial=DEST.with_suffix(DEST.suffix+'.partial')
    if DEST.exists():
        if DEST.stat().st_size!=size or checksum(DEST)!=expected:raise RuntimeError('Existing target differs; refusing to overwrite')
        print('Already present and verified',flush=True)
    elif args.parallel:
        parallel_download(partial,size,expected)
    else:
        for attempt in range(3):
            start=partial.stat().st_size if partial.exists() else 0
            if start==size:break
            if start>size:raise RuntimeError('Partial file is larger than expected')
            headers={'User-Agent':'niulai-local-setup'}
            if start:headers['Range']=f'bytes={start}-'
            try:
                with urllib.request.urlopen(urllib.request.Request(URL,headers=headers),timeout=60) as r:
                    if start and r.status!=206:start=0
                    if start and not r.headers.get('Content-Range','').startswith(f'bytes {start}-'):raise RuntimeError('Unexpected range response')
                    with partial.open('ab' if start else 'wb') as f:
                        done=start;last=time.monotonic()
                        while chunk:=r.read(4*1024*1024):
                            f.write(chunk);done+=len(chunk)
                            if done>size:raise RuntimeError('Response exceeds expected model size')
                            if time.monotonic()-last>=5:
                                print(f'DOWNLOAD {done}/{size} {done/size:.1%}',flush=True);last=time.monotonic()
                if partial.stat().st_size==size:break
            except (urllib.error.URLError,TimeoutError,OSError) as e:
                print('DOWNLOAD_RETRY',attempt+1,type(e).__name__,getattr(e,'code',''),flush=True)
                if attempt==2:raise RuntimeError('Download interrupted; partial file preserved') from None
        if partial.stat().st_size!=size:raise RuntimeError('Incomplete download; partial preserved')
        actual=checksum(partial)
        if actual!=expected:raise RuntimeError('SHA256 mismatch; partial preserved, not installed')
        partial.rename(DEST)
    with DEST.open('rb') as f:
        length=struct.unpack('<Q',f.read(8))[0]
        if length>100*1024*1024:raise RuntimeError('Invalid safetensors header size')
        header=json.loads(f.read(length))
    audit={'file':str(DEST),'source':URL,'bytes':size,'sha256':expected,'sha256_verified':True,'tensor_count':len(header)-('__metadata__' in header),'completed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    (AUDIT/'patch_install.json').write_text(json.dumps(audit,indent=2),encoding='utf8')
    print('PATCH_VERIFIED',size,expected,flush=True)

if __name__=='__main__':main()
