class_name PlayerAttacks
## 主角招式表。调手感主要改这里：帧数、击退、顿帧时长、震屏强度。
##
## 地面：J J J（刺拳-刺拳-回旋踢）  J J U（刺拳-刺拳-重拳）  U 重拳  W+J 上勾拳（挑空）
## 空中：J J（空中踢两段）  U 下劈（把敌人砸向地面，会弹起来）


static func build() -> Dictionary:
	var list: Array[AttackData] = [
		AttackData.make({
			"id": &"jab1", "startup": 3, "active": 3, "recovery": 12, "cancel_after": 3,
			"damage": 6, "knockback": Vector2(90, 0), "hitstop": 0.055, "shake": 0.12, "stagger": 0.32,
			"hitbox_offset": Vector2(20, -34), "hitbox_size": Vector2(22, 12),
			"lunge": 130.0, "next_combo": &"jab2",
		}),
		AttackData.make({
			"id": &"jab2", "startup": 3, "active": 3, "recovery": 12, "cancel_after": 3,
			"damage": 6, "knockback": Vector2(100, 0), "hitstop": 0.055, "shake": 0.12, "stagger": 0.32,
			"hitbox_offset": Vector2(21, -30), "hitbox_size": Vector2(22, 12),
			"lunge": 130.0, "next_combo": &"kick3",
		}),
		AttackData.make({
			"id": &"kick3", "startup": 6, "active": 4, "recovery": 20, "cancel_after": 99,
			"damage": 14, "knockback": Vector2(300, -110), "hitstop": 0.1, "shake": 0.35, "stagger": 0.5,
			"heavy": true, "hitbox_offset": Vector2(22, -22), "hitbox_size": Vector2(28, 16),
			"lunge": 220.0, "limb": AttackData.Limb.FOOT,
			"sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
		}),
		AttackData.make({
			"id": &"power", "startup": 11, "active": 4, "recovery": 22, "cancel_after": 99,
			"damage": 22, "knockback": Vector2(430, -60), "hitstop": 0.14, "shake": 0.55, "stagger": 0.6,
			"heavy": true, "hitbox_offset": Vector2(24, -32), "hitbox_size": Vector2(30, 16),
			"lunge": 300.0, "sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
		}),
		AttackData.make({
			"id": &"uppercut", "startup": 5, "active": 5, "recovery": 18, "cancel_after": 99,
			"damage": 10, "knockback": Vector2(15, -300), "hitstop": 0.09, "shake": 0.3, "stagger": 0.6,
			"launcher": true, "hitbox_offset": Vector2(14, -44), "hitbox_size": Vector2(20, 26),
			"lunge": 60.0, "sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
		}),
		AttackData.make({
			"id": &"air_kick1", "startup": 3, "active": 5, "recovery": 9, "cancel_after": 2, "air": true,
			"damage": 7, "knockback": Vector2(35, -40), "hitstop": 0.06, "shake": 0.15, "stagger": 0.4,
			"hitbox_offset": Vector2(18, -16), "hitbox_size": Vector2(24, 16),
			"limb": AttackData.Limb.FOOT, "next_combo": &"air_kick2",
		}),
		AttackData.make({
			"id": &"air_kick2", "startup": 3, "active": 5, "recovery": 10, "cancel_after": 2, "air": true,
			"damage": 7, "knockback": Vector2(60, -60), "hitstop": 0.06, "shake": 0.15, "stagger": 0.4,
			"hitbox_offset": Vector2(19, -22), "hitbox_size": Vector2(24, 16),
			"limb": AttackData.Limb.FOOT,
		}),
		AttackData.make({
			"id": &"air_spike", "startup": 7, "active": 5, "recovery": 14, "cancel_after": 99, "air": true,
			"damage": 14, "knockback": Vector2(140, 380), "hitstop": 0.12, "shake": 0.5, "stagger": 0.6,
			"heavy": true, "hitbox_offset": Vector2(16, -12), "hitbox_size": Vector2(28, 22),
			"sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
		}),
	]
	var table := {}
	for a in list:
		table[a.id] = a
	return table
