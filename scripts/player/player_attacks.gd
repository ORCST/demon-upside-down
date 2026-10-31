class_name PlayerAttacks
## 主角招式表。调手感主要改这里：帧数、击退、顿帧时长、震屏强度。
##
## 地面：J J J（Heavy Combo 三刀：下撩 - 过肩斜劈 - 后仰砸地）  J J U（两刀接重击）  U 重击  W+J 上挑（挑空）
## 空中：J J（空中斩两段）  U 下劈（把敌人砸向地面，会弹起来）
##
## hc1-hc3 的画面来自 3D 牛来渲染（art_source/3d/render/heavy_combo_v01），
## anim_timing 每一项对应一张 12fps 精灵帧，数值是它停留的物理帧数（60fps）；
## startup / active / recovery 要和 anim_timing 对齐：startup = 命中帧之前所有帧之和。


static func build() -> Dictionary:
	var list: Array[AttackData] = [
		# R002 R004 R006 R008 | R010 挥动 | R012 命中 | R014 R016 收势
		AttackData.make({
			"id": &"hc1", "startup": 19, "active": 6, "recovery": 15, "cancel_after": 4,
			"damage": 10, "knockback": Vector2(140, -20), "hitstop": 0.07, "shake": 0.22, "stagger": 0.38,
			"hitbox_offset": Vector2(40, -20), "hitbox_size": Vector2(62, 30),
			"lunge": 210.0, "next_combo": &"hc2",
			"sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
			"anim": &"hc1", "anim_timing": PackedInt32Array([4, 4, 4, 5, 2, 6, 7, 8]),
			"trail": Vector3(185, 25, 56), "trail_center": Vector2(2, -24),
		}),
		# R018 R020 R022 举剑 | R024 挥动 | R026 命中 | R028 R030 回扫
		AttackData.make({
			"id": &"hc2", "startup": 14, "active": 6, "recovery": 16, "cancel_after": 4,
			"damage": 12, "knockback": Vector2(170, -40), "hitstop": 0.08, "shake": 0.26, "stagger": 0.42,
			"hitbox_offset": Vector2(36, -26), "hitbox_size": Vector2(56, 44),
			"lunge": 170.0, "next_combo": &"hc3",
			"sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
			"anim": &"hc2", "anim_timing": PackedInt32Array([4, 4, 4, 2, 6, 7, 9]),
			"trail": Vector3(-95, 45, 58), "trail_center": Vector2(4, -30),
		}),
		# R030 R052 R056 R058 R060 后仰蓄力 | R062 举过头顶（停顿） | R064 砸地命中 | R066 + 压地停顿 + 起身
		AttackData.make({
			"id": &"hc3", "startup": 27, "active": 8, "recovery": 43, "cancel_after": 99,
			"damage": 24, "knockback": Vector2(380, -140), "hitstop": 0.16, "shake": 0.6, "stagger": 0.7,
			"heavy": true, "hitbox_offset": Vector2(42, -14), "hitbox_size": Vector2(74, 30),
			"lunge": 130.0, "sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
			"anim": &"hc3", "anim_timing": PackedInt32Array([4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6, 9]),
			"trail": Vector3(-105, 15, 62), "trail_center": Vector2(4, -22),
		}),
		AttackData.make({
			"id": &"power", "startup": 11, "active": 4, "recovery": 22, "cancel_after": 99,
			"damage": 22, "knockback": Vector2(430, -60), "hitstop": 0.14, "shake": 0.55, "stagger": 0.6,
			"heavy": true, "hitbox_offset": Vector2(36, -26), "hitbox_size": Vector2(56, 30),
			"lunge": 300.0, "sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
			"anim": &"atk_power", "trail": Vector3(-80, 60, 54), "trail_center": Vector2(6, -28),
		}),
		AttackData.make({
			"id": &"uppercut", "startup": 5, "active": 5, "recovery": 18, "cancel_after": 99,
			"damage": 10, "knockback": Vector2(15, -300), "hitstop": 0.09, "shake": 0.3, "stagger": 0.6,
			"launcher": true, "hitbox_offset": Vector2(22, -46), "hitbox_size": Vector2(34, 40),
			"lunge": 60.0, "sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
			"anim": &"atk_uppercut", "trail": Vector3(70, -80, 48), "trail_center": Vector2(4, -20),
		}),
		AttackData.make({
			"id": &"air_kick1", "startup": 3, "active": 5, "recovery": 9, "cancel_after": 2, "air": true,
			"damage": 7, "knockback": Vector2(35, -40), "hitstop": 0.06, "shake": 0.15, "stagger": 0.4,
			"hitbox_offset": Vector2(28, -24), "hitbox_size": Vector2(40, 26), "next_combo": &"air_kick2",
			"anim": &"atk_air", "trail": Vector3(-60, 50, 44), "trail_center": Vector2(2, -26),
		}),
		AttackData.make({
			"id": &"air_kick2", "startup": 3, "active": 5, "recovery": 10, "cancel_after": 2, "air": true,
			"damage": 7, "knockback": Vector2(60, -60), "hitstop": 0.06, "shake": 0.15, "stagger": 0.4,
			"hitbox_offset": Vector2(28, -24), "hitbox_size": Vector2(40, 26),
			"anim": &"atk_air", "trail": Vector3(60, -50, 44), "trail_center": Vector2(2, -26),
		}),
		AttackData.make({
			"id": &"air_spike", "startup": 7, "active": 5, "recovery": 14, "cancel_after": 99, "air": true,
			"damage": 14, "knockback": Vector2(140, 380), "hitstop": 0.12, "shake": 0.5, "stagger": 0.6,
			"heavy": true, "hitbox_offset": Vector2(18, -6), "hitbox_size": Vector2(34, 30),
			"sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
			"anim": &"atk_spike", "trail": Vector3(-30, 100, 40), "trail_center": Vector2(0, -24),
		}),
	]
	var table := {}
	for a in list:
		assert(a.anim_timing.is_empty() or _sum(a.anim_timing) == a.total_frames, "%s: anim_timing 之和要等于总帧数" % a.id)
		table[a.id] = a
	return table


static func _sum(values: PackedInt32Array) -> int:
	var s := 0
	for v in values:
		s += v
	return s
