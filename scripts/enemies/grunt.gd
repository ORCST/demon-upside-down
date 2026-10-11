extends Enemy
## 小恶魔：靠近玩家 → 后仰蓄力（变红 = 警告）→ 冲拳 → 收招。蓄力时挨打会被打断。

enum AI { CHASE, WINDUP, STRIKE, RECOVER }

@export var move_speed := 55.0
@export var aggro_range := 220.0
@export var attack_range := 34.0

var punch := AttackData.make({
	"id": &"grunt_punch", "startup": 28, "active": 5, "recovery": 36,
	"damage": 1, "knockback": Vector2(220, -140), "hitstop": 0.1, "shake": 0.45, "stagger": 0.35,
	"heavy": true, "hitbox_offset": Vector2(20, -32), "hitbox_size": Vector2(26, 16),
	"lunge": 160.0, "sfx_whoosh": "whoosh_heavy", "sfx_hit": "hit_heavy",
})

var _ai := AI.CHASE
var _t := 0
var _cooldown := 0.0
var _phase := 0.0

@onready var hitbox: Hitbox = $Hitbox


func _act(delta: float) -> void:
	_fall(delta)
	_cooldown -= delta
	match _ai:
		AI.CHASE:
			var p := get_tree().get_first_node_in_group(&"player") as Player
			var dx := 0.0
			if p:
				dx = p.global_position.x - global_position.x
			if p and p.is_alive() and absf(dx) < aggro_range:
				facing = 1 if dx > 0.0 else -1
				if absf(dx) > attack_range:
					velocity.x = move_toward(velocity.x, facing * move_speed, 500.0 * delta)
				else:
					velocity.x = move_toward(velocity.x, 0.0, 800.0 * delta)
					if _cooldown <= 0.0:
						_ai = AI.WINDUP
						_t = 0
						Sfx.play("warn", -6.0)
			else:
				velocity.x = move_toward(velocity.x, 0.0, 800.0 * delta)
		AI.WINDUP:
			_t += 1
			velocity.x = move_toward(velocity.x, 0.0, 800.0 * delta)
			if _t >= punch.startup:
				_ai = AI.STRIKE
				_t = 0
				hitbox.activate(punch, facing)
				velocity.x = facing * punch.lunge
				Sfx.play(punch.sfx_whoosh, -4.0)
		AI.STRIKE:
			_t += 1
			_friction(delta)
			if _t >= punch.active:
				hitbox.deactivate()
				_ai = AI.RECOVER
				_t = 0
		AI.RECOVER:
			_t += 1
			_friction(delta)
			if _t >= punch.recovery:
				_ai = AI.CHASE
				_cooldown = randf_range(0.4, 1.0)


func _interrupt() -> void:
	hitbox.deactivate()
	_ai = AI.CHASE
	_cooldown = 0.6


func _pose_act(delta: float) -> void:
	match _ai:
		AI.CHASE:
			var ratio := clampf(absf(velocity.x) / move_speed, 0.0, 1.0)
			_phase += delta * 12.0 * ratio
			rig.run_phase = _phase
			rig.run_amount = ratio
			rig.lean = 0.15 * ratio
		AI.WINDUP:
			var k := float(_t) / punch.startup
			rig.lean = -0.35 * k
			rig.fist = Vector2(-6, -28)
			rig.tint = Color(1, 0.15, 0.1)
			rig.tint_amount = 0.25 + 0.45 * k * (0.5 + 0.5 * sin(_t * 0.8))
		AI.STRIKE:
			rig.lean = 0.45
			rig.fist = punch.hitbox_offset + Vector2(6, 0)
			rig.fist_big = true
		AI.RECOVER:
			var k := float(_t) / punch.recovery
			rig.lean = 0.45 * (1.0 - k)
			rig.fist = (punch.hitbox_offset + Vector2(6, 0)).lerp(Vector2(9, -32), minf(k * 2.0, 1.0))
