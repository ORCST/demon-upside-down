import bpy,json
from pathlib import Path
p=Path('D:/GoDOTProject/demon_unside_down');bpy.ops.wm.open_mainfile(filepath=str(p/'outputs/motion_reference_20261015/ual2_review.blend'))
for o in bpy.context.scene.objects:
 print('OBJ',o.name,o.type,'parent',o.parent.name if o.parent else None,'loc',tuple(round(v,3) for v in o.location),'verts',len(o.data.vertices) if o.type=='MESH' else '')
a=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
print('ARM',a.name)
for b in a.data.bones:
 if b.name in ['root','pelvis','spine_01','spine_02','spine_03','neck_01','Head','upperarm_r','lowerarm_r','hand_r','thigh_r','calf_r','foot_r']:
  print('BONE',b.name,'parent',b.parent.name if b.parent else None,'head',tuple(round(v,3) for v in b.head_local),'length',round(b.length,3))
