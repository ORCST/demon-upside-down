class_name AttackData
extends Resource
## 一招攻击的全部数据，帧数按 60fps 计。
## 换成精灵动画时：startup / active / recovery 直接对应动画的 预备 / 出招 / 收招 三段帧。

@export var id: StringName

@export_group("帧数 (60fps)")
@export var startup := 4
@export var active := 3
@export var recovery := 10
## 收招开始后第几帧起，可以接下一招（连段窗口）
@export var cancel_after := 4

@export_group("伤害与反馈")
@export var damage := 6
## 击退速度，朝右为正；命中时按出招方向翻转
@export var knockback := Vector2(100, 0)
@export var hitstop := 0.06
@export var shake := 0.15
## 对手的受击硬直（秒）
@export var stagger := 0.3
@export var launcher := false
@export var heavy := false

@export_group("判定框")
## 以角色脚底为原点、朝右时的位置
@export var hitbox_offset := Vector2(20, -32)
@export var hitbox_size := Vector2(22, 12)

@export_group("动作")
## 出招瞬间向前冲的速度
@export var lunge := 120.0
@export var air := false
@export var next_combo: StringName = &""
@export var sfx_whoosh := "whoosh_light"
@export var sfx_hit := "hit_light"

@export_group("表现")
## 精灵动画名（assets/sprites/niulai3d/niulai3d.tres）
@export var anim: StringName = &""
## 每个动画帧持续的物理帧数；为空时出招前显示第 0 帧、之后第 1 帧
@export var anim_timing := PackedInt32Array()
## 刀光：x = 起始角度, y = 结束角度（度，朝右为准，90 = 正下方）, z = 半径；z = 0 不画
@export var trail := Vector3.ZERO
@export var trail_center := Vector2(0, -26)

var total_frames: int:
	get:
		return startup + active + recovery


static func make(props: Dictionary) -> AttackData:
	var a := AttackData.new()
	for key in props:
		a.set(key, props[key])
	return a
