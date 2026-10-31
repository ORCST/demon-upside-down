"""Prepare an environment-only kit from the approved forest concept.

Artwork is isolated/reconstructed with image_gen. This script only sizes,
maps the shared palette, cleans binary alpha, prepares modular joins and
builds material QA sheets. It never assembles or edits a game level.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from build_castle_c_assets import area, periodic, snap, outlined, opaque

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'art_source/environment/forest_v01'
REF = ROOT/'art_source/environment/forest_scene_concept_v01/forest_moonlight_ruins_v01.png'
NEAREST = Image.Resampling.NEAREST
BOX = Image.Resampling.BOX
SOURCES = {}

SIZES = {
    'sky_far':(640,360), 'mid_forest':(640,360),
    'tree_left':(224,360), 'tree_hollow':(256,360),
    'terrain_top':(64,16), 'terrain_body':(64,64),
    'terrain_edge_left':(16,80), 'terrain_edge_right':(16,80),
    'stone_ledge':(96,48), 'ruin_pillar':(48,144),
    'branch_platform':(96,32), 'bridge':(192,64), 'water':(128,64),
    'mushrooms':(64,48), 'hoof_sign':(48,56), 'cowbell':(32,40),
    'fern':(96,96), 'rocks':(96,64), 'fg_fern':(160,160), 'fg_tree':(96,360),
}


def raw(name, crop=True):
    candidates=sorted((BASE/'raw').glob(name+'_attempt*.png'))
    if not candidates: raise FileNotFoundError('Missing source '+name)
    path=candidates[-1]
    im=Image.open(path).convert('RGBA')
    bbox=im.getchannel('A').point(lambda v:255 if v>=64 else 0).getbbox()
    if not bbox: raise ValueError('Empty raw asset '+name)
    SOURCES[name]={'file':str(path.relative_to(ROOT)), 'original_size':list(im.size),
                   'crop_bbox':list(bbox) if crop else [0,0,im.width,im.height]}
    return im.crop(bbox) if crop else im


def make_palette():
    source=Image.open(REF).convert('RGB')
    regions=[(.40,.03,.71,.70), (0,0,.41,.32), (0,.10,.33,.55),
             (.69,.75,.98,.91), (.30,.72,.67,.86), (0,.88,1,1),
             (.78,.25,1,.66), (0,.55,.14,.71)]
    sheet=Image.new('RGB',(640,320))
    for i,region in enumerate(regions):
        box=tuple(int(v*(source.width if j%2==0 else source.height)) for j,v in enumerate(region))
        sheet.paste(source.crop(box).resize((160,160),BOX),((i%4)*160,(i//4)*160))
    indexed=sheet.quantize(colors=32,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    colors=np.array(indexed.getpalette()[:96],dtype=np.uint8).reshape(32,3)
    colors=colors[np.argsort(colors@np.array([.2126,.7152,.0722]))]
    highlights=[]
    for region in [(.535,.11,.61,.235),(.91,.37,.98,.53)]:
        box=tuple(int(v*(source.width if j%2==0 else source.height)) for j,v in enumerate(region))
        p=source.crop(box).quantize(colors=6,dither=Image.Dither.NONE)
        options=np.array(p.getpalette()[:18],dtype=np.uint8).reshape(6,3)
        extra=options[np.argmax(options@np.array([.2126,.7152,.0722]))]
        if not any(np.array_equal(extra,c) for c in colors):
            d=colors.astype(np.int32)[:,None,:]-colors.astype(np.int32)[None,:,:]
            distances=(d*d).sum(2).astype(float)
            distances[np.tril_indices(32)]=np.inf
            distances[:3,:]=np.inf
            distances[:,28:]=np.inf
            _,replace=np.unravel_index(np.argmin(distances),distances.shape)
            colors[replace]=extra
        highlights.append(extra.tolist())
    material_accents=[]
    for region in [(.33,.745,.64,.775),(.032,.58,.072,.635)]:
        box=tuple(int(v*(source.width if j%2==0 else source.height)) for j,v in enumerate(region))
        crop=source.crop(box).quantize(colors=8,dither=Image.Dither.NONE)
        cp=np.array(crop.getpalette()[:24],dtype=np.uint8).reshape(8,3)
        counts={index:count for count,index in crop.getcolors()}
        warm=[i for i,c in enumerate(cp.astype(float)) if c[0]>c[1]*1.2 and c[1]>c[2]*1.12 and c[0]>100]
        if not warm: continue
        extra=cp[max(warm,key=lambda i:counts.get(i,0))]
        if not any(np.array_equal(extra,c) for c in colors):
            d=colors.astype(np.int32)[:,None,:]-colors.astype(np.int32)[None,:,:]
            distances=(d*d).sum(2).astype(float)
            distances[np.tril_indices(32)]=np.inf
            candidates=(colors[:,2]>colors[:,0])&(colors@np.array([.2126,.7152,.0722])>25)
            distances[~candidates,:]=np.inf
            distances[:,~candidates]=np.inf
            _,replace=np.unravel_index(np.argmin(distances),distances.shape)
            colors[replace]=extra
        material_accents.append(extra.tolist())
    colors=colors[np.argsort(colors@np.array([.2126,.7152,.0722]))]
    assert len(np.unique(colors,axis=0))==32
    pal=Image.new('P',(1,1))
    pal.putpalette(colors.flatten().tolist()+colors[0].tolist()*224)
    Image.fromarray(colors.reshape(1,32,3),'RGB').save(BASE/'palette_forest.png')
    info={'source':str(REF.relative_to(ROOT)),'method':'Balanced8-region median-cut32, protected feature highlights, no dithering',
          'regions_normalized':regions,'protected_highlights':highlights,'material_accents':material_accents,
          'colors':[{'index':i,'rgb':c.tolist(),'hex':'#'+bytes(c).hex()} for i,c in enumerate(colors)],'outline_index':0}
    (BASE/'palette_forest.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    return colors,pal


def fit(name,size,pal,outline=None):
    source=raw(name)
    pad=1
    factor=min((size[0]-2*pad)/source.width,(size[1]-2*pad)/source.height)
    wh=(max(1,round(source.width*factor)),max(1,round(source.height*factor)))
    small=area(source,wh)
    out=Image.new('RGBA',size)
    out.alpha_composite(small,((size[0]-wh[0])//2,size[1]-wh[1]-pad))
    out=snap(out,pal)
    return outlined(out,outline) if outline is not None else out


def fill_texture(im,pal,colors):
    a=np.array(im)
    active=a[:,:,3]>=160
    if not active.any(): raise ValueError('No opaque texture interior')
    target=np.median(a[:,:,:3][active],axis=0)
    index=np.argmin(((colors.astype(float)-target)**2).sum(1))
    return opaque(im,colors[index])


def modular(im,left,right,pal):
    out=im.copy()
    mid=snap(periodic(out.crop((left,0,im.width-right,im.height)),'x',4),pal)
    out.paste(mid,(left,0))
    ar=np.array(out)
    ar[:,left-1]=ar[:,left]
    ar[:,im.width-right]=ar[:,im.width-right-1]
    return Image.fromarray(ar,'RGBA')


def silhouette(im,colors,pal,size=None):
    if size is not None: im=snap(area(im,size),pal)
    ar=np.array(im)
    active=ar[:,:,3]>0
    light=ar[:,:,:3]@np.array([.2126,.7152,.0722])
    cuts=np.quantile(light[active],[.45,.90])
    mapped=colors[np.digitize(light,cuts)]
    mapped[~active]=0
    return Image.fromarray(np.dstack((mapped,ar[:,:,3])),'RGBA')


def extend(im,left,right,copies=3):
    mid=im.crop((left,0,im.width-right,im.height))
    out=Image.new('RGBA',(left+mid.width*copies+right,im.height))
    out.alpha_composite(im.crop((0,0,left,im.height)))
    for i in range(copies): out.alpha_composite(mid,(left+i*mid.width,0))
    out.alpha_composite(im.crop((im.width-right,0,im.width,im.height)),(left+copies*mid.width,0))
    return out


def contact_sheet(assets,colors):
    out=Image.new('RGB',(1280,1320),(43,39,57))
    draw=ImageDraw.Draw(out)
    font=ImageFont.load_default()
    for i,(name,im) in enumerate(assets.items()):
        x,y=(i%5)*256,(i//5)*320
        draw.text((x+6,y+7),name+' '+str(im.size),font=font,fill=(240,226,204))
        for yy in range(y+30,y+308,12):
            for xx in range(x+4,x+252,12):
                fill=(61,57,72) if ((xx-x)//12+(yy-y)//12)%2 else (79,74,90)
                draw.rectangle((xx,yy,xx+11,yy+11),fill=fill)
        scale=min(240/im.width,268/im.height,3)
        small=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),NEAREST)
        out.paste(small,(x+(256-small.width)//2,y+35),small)
    for i,c in enumerate(colors): draw.rectangle((40*i,1290,40*i+39,1319),fill=tuple(map(int,c)))
    return out


def build():
    BASE.mkdir(exist_ok=True,parents=True)
    qa=BASE/'qa'
    qa.mkdir(exist_ok=True)
    colors,pal=make_palette()
    assets={}
    assets['sky_far']=snap(periodic(area(raw('sky_far',False),(640,360)),'x',20),pal)
    assets['sky_far']=opaque(assets['sky_far'],colors[5])
    assets['mid_forest']=snap(periodic(area(raw('mid_forest',False),(640,360)),'x',8),pal)
    assets['tree_left']=fit('tree_left',(224,360),pal)
    assets['tree_hollow']=fit('tree_hollow',(256,360),pal)

    terrain=raw('terrain')
    ta=np.array(terrain)
    green=(ta[:,:,1].astype(float)>ta[:,:,0]*1.04)&(ta[:,:,1].astype(float)>ta[:,:,2]*1.05)&(ta[:,:,3]>64)
    rows=np.where(green[:terrain.height//2].mean(1)>.015)[0]
    split=int(rows[-1]+2) if len(rows) else terrain.height//5
    split=min(max(split,terrain.height//10),terrain.height//2)
    SOURCES['terrain']['grass_soil_split_y']=split
    top=area(terrain.crop((0,0,terrain.width,split)),(64,16))
    body=fill_texture(area(terrain.crop((0,split,terrain.width,terrain.height)),(64,64)),pal,colors)
    body=body.filter(ImageFilter.MedianFilter(3))
    assets['terrain_top']=snap(periodic(top,'x',4),pal)
    assets['terrain_body']=snap(periodic(body,'xy',5),pal)
    full=Image.new('RGBA',(64,80))
    full.alpha_composite(assets['terrain_top'])
    full.alpha_composite(assets['terrain_body'],(0,16))
    for side in ['left','right']:
        edge=np.array(full.crop((0,0,16,80) if side=='left' else (48,0,64,80)))
        x=0 if side=='left' else 15
        active=edge[:,x,3]>0
        edge[active,x,:3]=colors[0]
        assets['terrain_edge_'+side]=Image.fromarray(edge,'RGBA')

    assets['stone_ledge']=modular(fit('stone_ledge',(96,48),pal),16,16,pal)
    assets['ruin_pillar']=fit('ruin_pillar',(48,144),pal)
    assets['branch_platform']=modular(fit('branch_platform',(96,32),pal),16,16,pal)
    assets['bridge']=modular(fit('bridge',(192,64),pal),48,48,pal)
    assets['water']=snap(periodic(fill_texture(area(raw('water',False),(128,64)),pal,colors),'x',8),pal)
    for name in ['mushrooms','hoof_sign','cowbell','fern','rocks']:
        assets[name]=fit(name,SIZES[name],pal,colors[0])
    dark=colors[[0,2,4]]
    assets['fg_fern']=silhouette(assets['fern'],dark,pal,(160,160))
    assets['fg_tree']=silhouette(assets['tree_left'].crop((64,0,160,360)),dark,pal)
    for name,im in assets.items(): im.save(BASE/(name+'.png'))

    tiling={'sky_far':'x','mid_forest':'x','terrain_top':'x','terrain_body':'xy','water':'x'}
    for name,axes in tiling.items():
        im=assets[name]
        nx,ny=(3 if 'x' in axes else 1),(3 if 'y' in axes else 1)
        tile=Image.new('RGBA',(im.width*nx,im.height*ny))
        for yy in range(ny):
            for xx in range(nx):tile.alpha_composite(im,(xx*im.width,yy*im.height))
        tile.save(qa/(name+'_repeat.png'))
    joints={'stone_ledge':(16,16),'branch_platform':(16,16),'bridge':(48,48)}
    for name,(left,right) in joints.items(): extend(assets[name],left,right).save(qa/(name+'_extended.png'))
    contact_sheet(assets,colors).save(qa/'asset_contact_sheet.png')
    validate(assets,colors,tiling,joints)
    print('Prepared',len(assets),'native environment assets;32-color palette; no level assembly')


def validate(assets,colors,tiling,joints):
    allowed={tuple(c) for c in colors.tolist()}
    records=[]
    for name,im in assets.items():
        assert im.size==SIZES[name],(name,im.size)
        ar=np.array(im); active=ar[:,:,3]>0
        assert set(np.unique(ar[:,:,3]))<={0,255},name
        assert active.any(),name
        used={tuple(c) for c in np.unique(ar[:,:,:3][active],axis=0).tolist()}
        assert used<=allowed,name
        seam={}
        for axis in tiling.get(name,''):
            a,b=(ar[:,0],ar[:,-1]) if axis=='x' else (ar[0],ar[-1])
            assert np.array_equal(a,b),(name,axis)
            seam[axis+'_boundary_equal']=True
        modular_info=None
        if name in joints:
            left,right=joints[name]
            assert np.array_equal(ar[:,left],ar[:,-right-1]),name
            assert np.array_equal(ar[:,left-1],ar[:,left]),name
            assert np.array_equal(ar[:,-right],ar[:,-right-1]),name
            middle=ar[:,left:im.width-right,3]
            coverage=(middle>0).mean(1)
            rows=np.where(coverage>=.85)[0]
            modular_info={'left':[0,0,left,im.height],
                'middle':[left,0,im.width-left-right,im.height],
                'right':[im.width-right,0,right,im.height],
                'middle_edges_equal':True,'first_continuous_surface_y':int(rows[0]) if len(rows) else None,
                'surface_y_is_visual_hint_not_collision_data':True}
        surface_rows=np.where((ar[:,:,3]>0).mean(1)>=.85)[0] if name=='terrain_top' else []
        records.append({'file':name+'.png','size':list(im.size),
            'colors':len(used),'transparent_pixels':int((~active).sum()),'bbox':im.getchannel('A').getbbox(),
            'continuous_grass_rim_y':int(surface_rows[0]) if len(surface_rows) else None,
            'tiling':seam,'modular':modular_info,
            'sha256':hashlib.sha256((BASE/(name+'.png')).read_bytes()).hexdigest()})
    for name in ['mid_forest','tree_left','tree_hollow','mushrooms','hoof_sign','cowbell','fern','rocks','bridge']:
        assert 0<np.array(assets[name])[:,:,3].sum()<assets[name].width*assets[name].height*255,name
    assert len(np.unique(np.array(assets['fg_fern'])[:,:,:3][np.array(assets['fg_fern'])[:,:,3]>0],axis=0))<=3
    assert Image.open(BASE/'palette_forest.png').size==(32,1)
    before=json.loads((BASE/'raw/protected_before.json').read_text(encoding='utf-8'))
    excluded=[p for p in before if p.startswith('art_source\\environment\\forest_scene_concept_v01\\') and Path(p).suffix in ['.md','.json','.txt']]
    checked={p:sha for p,sha in before.items() if p not in excluded}
    changed=[p for p,sha in checked.items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=sha]
    assert not changed,changed
    cfg=json.loads((BASE/'raw/prompts.json').read_text(encoding='utf-8'))
    calls=len(list((BASE/'raw').glob('*generation*.json')))
    report={'date':'2026-10-29','source_concept':str(REF.relative_to(ROOT)),
        'source_concept_approved_by_user':True,'authorization':'User said: 可以的拆分一下',
        'tool':'built-in image_gen','generation_calls':calls,
        'method':'Isolated/reconstructed occluded components using the approved concept, then area resize/palette/binary-alpha/join processing; not pixel-identical clipping.',
        'palette_colors':32,'assets':records,'selected_sources':SOURCES,
        'layer_order':['sky_far','mid_forest','tree_left/tree_hollow/ruin_pillar','terrain/platform/bridge/water','props','fg_fern/fg_tree'],
        'sky_note':'Moon, ruined tower and far conifers are combined in sky_far, not separate sprites.',
        'water_note':'Single static repeating texture, no water animation or physics implemented.',
        'protected_files_unchanged':len(checked),'allowed_source_metadata_updates':excluded,
        'level_assembly_or_game_integration':False,
        'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'review_status':'material_pack_for_Devin_integration_review'}
    (BASE/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':build()
