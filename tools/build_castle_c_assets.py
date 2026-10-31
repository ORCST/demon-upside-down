"""Build the user-requested Castle C kit from image_gen originals.

Only deterministic sizing, palette mapping, alpha/outline cleanup, periodic
edge conditioning, reuse of modular parts, QA and assembly are done here.
Original artwork remains in raw/. No game asset or scene is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'art_source/environment/castle_c_v01'
STYLE = ROOT / 'art_source/environment/castle_style_studies_20261029/castle_C_cartoon_v02.png'
BOX = Image.Resampling.BOX
NEAREST = Image.Resampling.NEAREST


def read_raw(name):
    p = BASE / 'raw' / (name + '_attempt01.png')
    second = p.with_name(name + '_attempt02.png')
    if second.exists(): p = second
    im = Image.open(p).convert('RGBA')
    if name == 'floor_top' and second.exists():
        data = np.array(im)
        data[np.min(data[:,:,:3],axis=2) >= 245,3] = 0
        im = Image.fromarray(data,'RGBA')
    bbox = im.getchannel('A').point(lambda v: 255 if v >= 64 else 0).getbbox()
    if not bbox:
        raise ValueError('Empty original: ' + name)
    return im.crop(bbox)


def area(im, size):
    return im.convert('RGBa').resize(size, BOX).convert('RGBA')


def periodic(im, axes='x', band=4):
    """Match opposite boundary bands before discrete palette/alpha mapping."""
    a = np.asarray(im.convert('RGBA'), dtype=np.float32).copy()
    for axis in axes:
        n = a.shape[1 if axis == 'x' else 0]
        b = min(band, n // 4)
        for k in range(b):
            w = (1.0 - k / b) ** 2
            if axis == 'x':
                lo, hi = a[:, k].copy(), a[:, -1-k].copy()
                mid = (lo + hi) / 2
                a[:, k], a[:, -1-k] = lo*(1-w)+mid*w, hi*(1-w)+mid*w
            else:
                lo, hi = a[k].copy(), a[-1-k].copy()
                mid = (lo + hi) / 2
                a[k], a[-1-k] = lo*(1-w)+mid*w, hi*(1-w)+mid*w
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def make_palette():
    source = Image.open(STYLE).convert('RGB')
    ref = source.resize((640, 360), BOX)
    sample = Image.new('RGB', (640,520))
    sample.paste(ref,(0,0))
    regions = [(.16,.27,.23,.46),(.30,.28,.37,.47),(.75,.28,.83,.48),(.34,.45,.54,.52)]
    for i,region in enumerate(regions):
        box = tuple(int(v * (source.width if j%2==0 else source.height)) for j,v in enumerate(region))
        sample.paste(source.crop(box).resize((160,160),BOX),(160*i,360))
    indexed = sample.quantize(colors=32, method=Image.Quantize.MEDIANCUT,
                           dither=Image.Dither.NONE)
    colors = np.array(indexed.getpalette()[:96], dtype=np.uint8).reshape(32, 3)
    colors = colors[np.argsort(colors @ np.array([.2126, .7152, .0722]))]
    highlights = []
    for region in [(.47,.18,.53,.29),(.17,.30,.22,.39)]:
        box = tuple(int(v*(source.width if j%2==0 else source.height)) for j,v in enumerate(region))
        crop = source.crop(box).quantize(colors=6, dither=Image.Dither.NONE)
        candidates = np.array(crop.getpalette()[:18],dtype=np.uint8).reshape(6,3)
        color = candidates[np.argmax(candidates @ np.array([.2126,.7152,.0722]))]
        diff = colors.astype(np.int32)[:,None,:]-colors.astype(np.int32)[None,:,:]
        distances = (diff*diff).sum(2).astype(float)
        distances[np.tril_indices(32)] = np.inf
        distances[:3,:] = np.inf
        distances[:,28:] = np.inf
        _, replace = np.unravel_index(np.argmin(distances),distances.shape)
        colors[replace] = color
        highlights.append(color.tolist())
    colors = colors[np.argsort(colors @ np.array([.2126,.7152,.0722]))]
    pal = Image.new('P', (1, 1))
    pal.putpalette(colors.flatten().tolist() + colors[0].tolist() * 224)
    Image.fromarray(colors.reshape(1, 32, 3), 'RGB').save(BASE/'palette_c.png')
    (BASE/'palette_c.json').write_text(json.dumps({
        'source': str(STYLE.relative_to(ROOT)), 'method': '640x360 full view plus four160x160 feature crops; median-cut32; no dithering; luminance sort',
        'feature_regions_normalized': regions,
        'protected_feature_highlights': highlights,
        'colors': [{'index': i, 'rgb': c.tolist(), 'hex': '#'+bytes(c).hex()} for i, c in enumerate(colors)],
        'outline_index': 0,
    }, indent=2)+'\n', encoding='utf-8')
    return colors, pal


def snap(im, pal):
    alpha = np.asarray(im.getchannel('A')) >= 128
    rgb = np.array(im.convert('RGB').quantize(palette=pal, dither=Image.Dither.NONE).convert('RGB'))
    rgb[~alpha] = 0
    return Image.fromarray(np.dstack((rgb, alpha.astype(np.uint8)*255)), 'RGBA')


def outlined(im, color):
    a = np.asarray(im.getchannel('A'))
    dilation = np.array(im.getchannel('A').filter(ImageFilter.MaxFilter(3)))
    result = np.array(im)
    new = (dilation > 0) & (a == 0)
    result[new, :3] = color
    result[new, 3] = 255
    return Image.fromarray(result, 'RGBA')


def opaque(im, color):
    bg = Image.new('RGBA', im.size, tuple(map(int, color))+(255,))
    bg.alpha_composite(im)
    return bg


def solid_part(name, size, pal, outline_color=None):
    padding = 1 if outline_color is not None else 0
    im = area(read_raw(name), (size[0]-2*padding, size[1]-2*padding))
    target = Image.new('RGBA', size)
    target.alpha_composite(im, (padding, padding))
    target = snap(target, pal)
    return outlined(target, outline_color) if outline_color is not None else target


def bounded_holes(frame):
    alpha = np.asarray(frame.getchannel('A'))
    empty = (alpha == 0).astype(np.uint8)
    _, labels = cv2.connectedComponents(empty, connectivity=4)
    exterior = set(np.concatenate((labels[0], labels[-1], labels[:,0], labels[:,-1])).tolist())
    holes = np.zeros(alpha.shape, bool)
    for label in np.unique(labels):
        region = labels == label
        if label != 0 and label not in exterior and region.sum() >= 20:
            holes |= region
    if holes.sum() < frame.width * frame.height * .2:
        raise ValueError('Window panes are not bounded transparent holes; inspect the generated frame')
    return holes


def wall_window(wall, frame, y):
    out = np.array(wall)
    x = (128-frame.width)//2
    holes = bounded_holes(frame)
    out[y:y+frame.height, x:x+frame.width][holes] = 0
    im = Image.fromarray(out, 'RGBA')
    im.alpha_composite(frame, (x, y))
    return im


def darken(im, colors):
    """Map existing shapes into the darkest three palette entries."""
    arr = np.asarray(im)
    levels = arr[:,:,:3] @ np.array([.2126, .7152, .0722])
    active = arr[:,:,3] > 0
    cuts = np.quantile(levels[active], [.35, .97])
    rgb = colors[np.digitize(levels, cuts)]
    rgb[~active] = 0
    return Image.fromarray(np.dstack((rgb, arr[:,:,3])), 'RGBA')


def build():
    BASE.mkdir(parents=True, exist_ok=True)
    qa = BASE/'qa'
    qa.mkdir(exist_ok=True)
    colors, pal = make_palette()
    assets = {}
    assets['sky_far'] = snap(periodic(area(read_raw('sky'), (640,360)), 'x', 24), pal)
    assets['sky_far'] = opaque(assets['sky_far'], colors[5])
    wall_tile = opaque(area(read_raw('wall_tile'), (128,192)), colors[15])
    wall_tile = wall_tile.filter(ImageFilter.MedianFilter(3))
    wall_tile = Image.blend(wall_tile,Image.new('RGBA',wall_tile.size,tuple(map(int,colors[17]))+(255,)),.22)
    wall_tile = snap(periodic(wall_tile, 'xy', 8), pal)
    wall = Image.new('RGBA', (128,384))
    for y in range(0,384,192): wall.alpha_composite(wall_tile, (0,y))
    assets['wall_plain'] = wall
    frame = solid_part('window_frame', (96,256), pal)
    assets['wall_window'] = wall_window(wall, frame, 80)
    small = snap(area(frame, (68,164)), pal)
    assets['wall_window_small'] = wall_window(wall, small, 172)
    assets['column'] = solid_part('column', (48,384), pal)
    assets['banner'] = solid_part('banner', (48,112), pal, colors[0])
    assets['chain'] = snap(periodic(area(read_raw('chain'), (12,64)), 'y', 6), pal)
    if not np.asarray(assets['chain'])[0,:,3].any():
        raise ValueError('Chain repeat ends are empty')
    assets['lantern'] = solid_part('lantern', (40,72), pal, colors[0])

    raw = Image.open(BASE/'raw/torch4_attempt01.png').convert('RGBA')
    cells, boxes, centers = [], [], []
    for i in range(4):
        cell = raw.crop((i*raw.width//4,0,(i+1)*raw.width//4,raw.height))
        bbox = cell.getchannel('A').point(lambda v: 255 if v>=64 else 0).getbbox()
        if not bbox: raise ValueError('Missing torch frame '+str(i))
        lower = cell.crop((0,raw.height//2,cell.width,raw.height)).getchannel('A').point(lambda v:255 if v>=64 else 0).getbbox()
        if not lower: raise ValueError('Missing torch bracket '+str(i))
        cells.append(cell)
        boxes.append(bbox)
        centers.append((lower[0]+lower[2])//2)
    top, bottom = min(b[1] for b in boxes), max(b[3] for b in boxes)
    left = min(b[0]-c for b,c in zip(boxes,centers))
    right = max(b[2]-c for b,c in zip(boxes,centers))
    frames = [snap(area(cell.crop((center+left,top,center+right,bottom)),(24,48)),pal)
              for cell,center in zip(cells,centers)]
    bracket = frames[0].crop((0,24,24,48))
    for frame_i in frames: frame_i.paste(bracket,(0,24))
    sheet = Image.new('RGBA',(96,48))
    for i,fr in enumerate(frames): sheet.alpha_composite(fr,(24*i,0))
    assets['torch'] = sheet

    cap = opaque(area(read_raw('floor_top'),(64,16)),colors[10])
    assets['floor_top'] = snap(periodic(cap,'x',4),pal)
    body_raw = read_raw('floor_body')
    if (BASE/'raw/floor_body_attempt02.png').exists():
        body_raw = body_raw.crop((0,int(body_raw.height*.235),body_raw.width,int(body_raw.height*.705)))
    body = opaque(area(body_raw,(64,64)),colors[4])
    body_pixels = np.array(body)
    body_pixels[32:] = np.roll(body_pixels[32:],16,axis=1)
    body = Image.fromarray(body_pixels,'RGBA')
    assets['floor_body'] = snap(periodic(body,'xy',6),pal)
    terrain = Image.new('RGBA',(64,80))
    terrain.alpha_composite(assets['floor_top'])
    terrain.alpha_composite(assets['floor_body'],(0,16))
    for side in ['left','right']:
        edge = np.array(terrain.crop((0,0,16,80) if side=='left' else (48,0,64,80)))
        boundary = slice(0,2) if side=='left' else slice(14,16)
        edge[:,boundary,:3] = colors[0]
        edge[:,boundary,3] = 255
        if side=='left': edge[0,:2] = 0
        else: edge[0,-2:] = 0
        assets['floor_edge_'+side] = Image.fromarray(edge,'RGBA')

    plank = solid_part('plank',(40,14),pal)
    middle = snap(periodic(plank.crop((12,0,28,14)),'x',3),pal)
    plank.paste(middle,(12,0))
    pa = np.array(plank)
    pa[:,11] = pa[:,12]
    pa[:,28] = pa[:,27]
    assets['plank'] = Image.fromarray(pa,'RGBA')
    foreground_colors = colors[[0,3,9]]
    assets['fg_fence'] = darken(solid_part('fg_fence',(160,160),pal,colors[0]), foreground_colors)
    assets['fg_pillar'] = darken(snap(area(assets['column'],(64,360)),pal), foreground_colors)
    for name,im in assets.items(): im.save(BASE/(name+'.png'))

    tile_axes = {'sky_far':'x','wall_plain':'x','floor_top':'x','floor_body':'xy','chain':'y'}
    for name, axes in tile_axes.items():
        im = assets[name]
        nx,ny = (3 if 'x' in axes else 1),(3 if 'y' in axes else 1)
        check = Image.new('RGBA',(im.width*nx,im.height*ny))
        for y in range(ny):
            for x in range(nx): check.alpha_composite(im,(x*im.width,y*im.height))
        check.save(qa/(name+'_repeat.png'))
    middle = assets['plank'].crop((12,0,28,14))
    check = Image.new('RGBA',(48,14))
    for x in range(0,48,16): check.alpha_composite(middle,(x,0))
    check.save(qa/'plank_middle_repeat.png')

    assemblies = [assemble(assets,i) for i in range(4)]
    assemblies[0].save(BASE/'assembly_native.png')
    assemblies[0].resize((1280,720),NEAREST).save(BASE/'assembly_preview.png')
    assemblies[0].resize((1280,720),NEAREST).save(BASE/'assembly_torch_loop.gif',save_all=True,
        append_images=[im.resize((1280,720),NEAREST) for im in assemblies[1:]],duration=140,loop=0,disposal=2)
    contact_sheet(assets,colors).save(qa/'asset_contact_sheet.png')
    validate(assets, colors, frames, tile_axes)
    print('Built',len(assets),'native assets; assembly1280x720; palette32; QA complete')


def platform(kit,width):
    out = Image.new('RGBA',(width,14))
    out.alpha_composite(kit.crop((0,0,12,14)))
    for x in range(12,width-12,16):
        n = min(16,width-12-x)
        out.alpha_composite(kit.crop((12,0,12+n,14)),(x,0))
    out.alpha_composite(kit.crop((28,0,40,14)),(width-12,0))
    return out


def block(assets,width,height):
    out = Image.new('RGBA',(width,height))
    for x in range(0,width,64):
        out.alpha_composite(assets['floor_top'],(x,0))
        for y in range(16,height,64): out.alpha_composite(assets['floor_body'],(x,y))
    out.alpha_composite(assets['floor_edge_left'].crop((0,0,16,min(80,height))),(0,0))
    out.alpha_composite(assets['floor_edge_right'].crop((0,0,16,min(80,height))),(width-16,0))
    return out


def assemble(a,frame):
    canvas = Image.fromarray(np.roll(np.array(a['sky_far']),-180,axis=1),'RGBA')
    for i in range(5):
        name = 'wall_window' if i in [0,3] else 'wall_window_small' if i==2 else 'wall_plain'
        canvas.alpha_composite(a[name],(128*i,-84))
    for x in [112,496]: canvas.alpha_composite(a['column'],(x,-40))
    for x in [208,548]: canvas.alpha_composite(a['banner'],(x,20))
    torch = a['torch'].crop((frame*24,0,frame*24+24,48))
    for x in [88,276,480]: canvas.alpha_composite(torch,(x,148))
    canvas.alpha_composite(a['chain'],(592,-28))
    canvas.alpha_composite(a['chain'],(592,36))
    canvas.alpha_composite(a['lantern'],(578,92))
    canvas.alpha_composite(block(a,640,80),(0,300))
    canvas.alpha_composite(block(a,144,32),(496,268))
    canvas.alpha_composite(platform(a['plank'],104),(254,210))
    canvas.alpha_composite(platform(a['plank'],88),(396,152))
    hero = Image.open(ROOT/'art_source/reference/poses/niulai_idle_tail_native.png').convert('RGBA')
    canvas.alpha_composite(hero,(48,92)) # native body-center112+48=160, soles207+92=299
    canvas.alpha_composite(a['fg_pillar'],(-48,0))
    canvas.alpha_composite(a['fg_fence'],(-80,220))
    canvas.alpha_composite(a['fg_fence'],(608,240))
    return canvas.convert('RGB')


def contact_sheet(assets,colors):
    canvas = Image.new('RGB',(1152,880),(48,42,58))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for idx,(name,im) in enumerate(assets.items()):
        x,y = (idx%6)*192,(idx//6)*280
        draw.text((x+5,y+5),name+' '+str(im.size),font=font,fill=(245,225,200))
        for cy in range(y+30,y+260,12):
            for cx in range(x+4,x+188,12):
                fill = (65,59,73) if ((cx-x)//12+(cy-y)//12)%2 else (80,73,88)
                draw.rectangle((cx,cy,cx+11,cy+11),fill=fill)
        factor = min(180/im.width,220/im.height,3)
        show = im.resize((max(1,int(im.width*factor)),max(1,int(im.height*factor))),NEAREST)
        canvas.paste(show,(x+(192-show.width)//2,y+35),show)
    for i,c in enumerate(colors): draw.rectangle((i*36,850,i*36+35,879),fill=tuple(map(int,c)))
    return canvas


def validate(assets,colors,frames,tile_axes):
    sizes={'sky_far':(640,360),'wall_plain':(128,384),'wall_window':(128,384),
        'wall_window_small':(128,384),'column':(48,384),'banner':(48,112),
        'torch':(96,48),'chain':(12,64),'lantern':(40,72),'floor_top':(64,16),
        'floor_body':(64,64),'floor_edge_left':(16,80),'floor_edge_right':(16,80),
        'plank':(40,14),'fg_fence':(160,160),'fg_pillar':(64,360)}
    palette_set={tuple(c) for c in colors.tolist()}
    records=[]
    for name,im in assets.items():
        assert im.size==sizes[name],(name,im.size)
        ar=np.array(im); visible=ar[:,:,3]>0
        assert set(np.unique(ar[:,:,3]))<={0,255},name
        used={tuple(c) for c in np.unique(ar[:,:,:3][visible],axis=0).tolist()}
        assert used<=palette_set,name
        assert visible.any(),name
        seams={}
        for axis in tile_axes.get(name,''):
            lo,hi=(ar[:,0],ar[:,-1]) if axis=='x' else (ar[0],ar[-1])
            seams[axis+'_opposite_boundary_exact']=bool(np.array_equal(lo,hi))
            assert np.array_equal(lo,hi),(name,axis)
        records.append({'file':name+'.png','size':list(im.size),'visible_pixels':int(visible.sum()),
            'transparent_pixels':int((~visible).sum()),'colors':len(used),'seams':seams,
            'sha256':hashlib.sha256((BASE/(name+'.png')).read_bytes()).hexdigest()})
    brackets=[np.array(f)[24:] for f in frames]
    assert all(np.array_equal(brackets[0],b) for b in brackets[1:])
    flame_hashes=[hashlib.sha256(np.array(f)[:24].tobytes()).hexdigest() for f in frames]
    assert len(set(flame_hashes))>=3, 'Flames do not vary'
    assert Image.open(BASE/'assembly_preview.png').size==(1280,720)
    native=np.array(Image.open(BASE/'assembly_native.png'))
    display=np.array(Image.open(BASE/'assembly_preview.png'))
    assert np.array_equal(display,np.repeat(np.repeat(native,2,0),2,1))
    before=json.loads((BASE/'raw/protected_before.json').read_text(encoding='utf-8'))
    modified=[p for p,sha in before.items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=sha]
    assert not modified,modified
    generations = [json.loads(p.read_text(encoding='utf-8')) for p in (BASE/'raw').glob('*generation*.json')]
    selected_sources = {name:str((BASE/'raw'/f'{name}_attempt{2 if (BASE/"raw"/f"{name}_attempt02.png").exists() else 1:02d}.png').relative_to(ROOT))
        for name in ['sky','wall_tile','window_frame','column','banner','torch4','chain','lantern','floor_top','floor_body','plank','fg_fence']}
    metadata={'palette_colors':32,'assets':records,'generation_calls':len(generations),
        'selected_sources':selected_sources,'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'torch':{'frames':4,'fps':1000/140,
        'frame_size':[24,48],'fixed_bracket_rect':[0,24,24,48],'brackets_identical':True,'unique_flames':len(set(flame_hashes))},
        'plank_regions':{'left':[0,0,12,14],'middle':[12,0,16,14],'right':[28,0,12,14]},
        'wall_origin_in_preview':[0,-84],'sky_offset_in_preview':[-180,0],'hero_canvas_offset':[48,92],
        'hero_source':'art_source/reference/poses/niulai_idle_tail_native.png',
        'assembly_native':[640,360],'assembly_preview':[1280,720],
        'nearest_neighbor2x_exact':True,'protected_files_unchanged':len(before),
        'review_status':'candidate_for_user_review_not_integrated',
        'note':'Periodic edge bands are repaired before palette mapping. Inspect triple-repeat QA for visible repetition, not only equality.'}
    (BASE/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.parse_args()
    build()
