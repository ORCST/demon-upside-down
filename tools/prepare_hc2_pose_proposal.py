"""Extract real cut2 reference frames before requesting Devin's pose review."""
import json,shutil
from pathlib import Path
import av
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'art_source/reference/pose_refs/heavy_combo_cut2_proposal'
VIDEO=ROOT/'outputs/motion_reference_20261015/clean_side/ual2__Sword_Heavy_Combo.mp4'
PROXY=ROOT/'art_source/control/heavy_combo_v02_39f/proxy/beauty'
WANTED=list(range(18,30))

def main():
    (OUT/'source').mkdir(parents=True,exist_ok=True);(OUT/'proxy').mkdir(exist_ok=True)
    with av.open(str(VIDEO)) as c:
        for i,f in enumerate(c.decode(video=0)):
            if i in WANTED:f.to_image().save(OUT/'source'/f'R{i:03d}.png')
            if i>=WANTED[-1]:break
    for i in WANTED:shutil.copy2(PROXY/f'R{i:03d}.png',OUT/'proxy'/f'R{i:03d}.png')
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    board=Image.new('RGB',(6*256,4*280),'#171c26');draw=ImageDraw.Draw(board)
    for n,i in enumerate(WANTED):
        for r,folder in enumerate(['source','proxy']):
            row=n//6*2+r;im=Image.open(OUT/folder/f'R{i:03d}.png').convert('RGB')
            # Same crop for every frame within each source; never crop each pose independently.
            if folder=='proxy':im=im.crop((73,270,695,675))
            im.thumbnail((256,256),Image.Resampling.LANCZOS);board.paste(im,(n%6*256+(256-im.width)//2,row*280+24))
            draw.text((n%6*256+6,row*280+2),f'R{i:03d} / {folder}',font=font,fill='white')
    board.save(OUT/'cut2_reference_contact_sheet.png')
    # A possible future segment start, prepared but never submitted to ComfyUI.
    first=Image.open(ROOT/'art_source/minimax/hc1_ctrl/native/hc1_ctrl_r012.png').convert('RGBA').resize((768,768),Image.Resampling.NEAREST)
    green=Image.new('RGBA',(768,768),(0,255,0,255));green.alpha_composite(first);green.convert('RGB').save(OUT/'input_R012_green768.png')
    manifest={'status':'reference_extraction_only_waiting_Devin_pose_review','source_video':VIDEO.relative_to(ROOT).as_posix(),'source_fps':24,'proposed_segment_source_range':[12,50],'segment_frames':39,
              'first_frame_source':'art_source/minimax/hc1_ctrl/native/hc1_ctrl_r012.png','primary_proposed_global_to_segment_indices':{'21':9,'27':15},
              'alternative_first_anchor_global_to_segment_indices':{'23':11},'deferred_reference_only_global_to_segment_indices':{'24':12,'26':14},
              'notes':['Pose descriptions must be checked against these real frames before image_gen.','R021 is upright sword lifting; R023 is closer to over-shoulder. R024 is still behind/high, not a forward downward strike midpoint.','R024/R026 are reference only, not anchors to draw in the current proposal.','No second-cut image generation, ControlNet sampling, independent recovery or third cut performed.']}
    (OUT/'reference_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print('Extracted source/proxy R018-R029 and prepared R012 green start; no generation')

if __name__=='__main__':main()
