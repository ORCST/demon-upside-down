class_name Player
extends CharacterBody2D
## 主角控制器：移动 / 跳跃 / 冲刺 / 大剑连段 / 受击。
## 输入用缓冲：顿帧冻结期间按下的键也会记住，解冻后立刻接招。

signal health_changed(current: int, max_health: int)

enum State { NORMAL, ATTACK, DASH, HURT, DEAD }

const INPUT_BUFFER := 0.15
const ONE_WAY_LAYER := 6

@export_group("移动")
@export var run_speed := 150.0
@export var ground_accel := 1400.0
@export var ground_decel := 1900.0
@export var air_accel := 1000.0
@export var gravity := 950.0
@export var fall_gravity_mult := 1.5
@export var max_fall_speed := 430.0
@export var jump_velocity := 330.0
## 松开跳跃键时上升速度保留的比例（小跳）
@export var jump_cut := 0.45
@export var coyote_time := 0.1

@export_group("冲刺")
@export var dash_speed := 400.0
@export var dash_time := 0.16
@export var dash_cooldown := 0.3

@export_group("能力（之后由地图里的道具解锁）")
@export var can_dash := true
@export var can_double_jump := true

@export_group("生命")
@export var max_health := 6
@export var invincible_time := 1.0

var state := State.NORMAL
var facing := 1
var health := 0
var attacks := {}

var _buf := {&"attack": 0.0, &"heavy": 0.0, &"jump": 0.0, &"dash": 0.0}
var _coyote := 0.0
var _air_jumps := 0
var _jump_held := false
var _dash_t := 0.0
var _dash_cd := 0.0
var _air_dash_used := false
var _attack: AttackData
var _attack_frame := 0
var _queued: StringName = &""
var _attack_hit := false
var _hurt_t := 0.0
var _invuln_t := 0.0
var _was_on_floor := true
var _fall_speed := 0.0
var _spawn_pos := Vector2.ZERO
var _frame := 0
var _land_t := 0.0

@onready var rig: NiulaiSprite = $Rig
@onready var hitbox: Hitbox = $Hitbox
@onready var hurtbox: Hurtbox = $Hurtbox


func _ready() -> void:
	health = max_health
	_spawn_pos = global_position
	attacks = PlayerAttacks.build()
	hitbox.landed.connect(_on_hit_landed)
	hurtbox.hurt.connect(_on_hurt)
	health_changed.emit.call_deferred(health, max_health)


func _unhandled_input(event: InputEvent) -> void:
	for action in _buf:
		if event.is_action_pressed(action):
			_buf[action] = INPUT_BUFFER


func _physics_process(delta: float) -> void:
	_frame += 1
	_tick_timers(delta)
	match state:
		State.NORMAL:
			_state_normal(delta)
		State.ATTACK:
			_state_attack(delta)
		State.DASH:
			_state_dash(delta)
		State.HURT:
			_state_hurt(delta)
		State.DEAD:
			_apply_gravity(delta)
			velocity.x = move_toward(velocity.x, 0.0, 400.0 * delta)
	_fall_speed = velocity.y
	move_and_slide()
	_after_move()
	_update_rig(delta)


# ---------------------------------------------------------------- 状态

func _state_normal(delta: float) -> void:
	var ix := Input.get_axis(&"move_left", &"move_right")
	var on_floor := is_on_floor()
	if on_floor:
		_coyote = coyote_time
		_air_jumps = 1 if can_double_jump else 0
		_air_dash_used = false
	if ix != 0.0:
		facing = 1 if ix > 0.0 else -1
	var accel := air_accel
	if on_floor:
		accel = ground_accel if ix != 0.0 else ground_decel
	velocity.x = move_toward(velocity.x, ix * run_speed, accel * delta)
	_apply_gravity(delta)

	if _try_attack():
		return
	if _buf[&"dash"] > 0.0 and _can_start_dash():
		_start_dash()
		return
	_try_jump()


func _state_attack(delta: float) -> void:
	var a := _attack
	_attack_frame += 1
	var f := _attack_frame
	var active_end := a.startup + a.active

	if a.air:
		_apply_gravity(delta, 0.55)
		var ix := Input.get_axis(&"move_left", &"move_right")
		if ix != 0.0:  # 不推摇杆就保持惯性，空中连段能跟住目标
			velocity.x = move_toward(velocity.x, ix * run_speed * 0.7, air_accel * 0.6 * delta)
		if is_on_floor() and f > 2:
			_end_attack()
			return
	else:
		_apply_gravity(delta)
		var decel := 2400.0 if f <= a.startup else 1300.0
		velocity.x = move_toward(velocity.x, 0.0, decel * delta)
		if _enemy_in_front(22.0):
			velocity.x = 0.0  # 冲拳贴到敌人就停，不会穿过去

	if f == a.startup + 1:
		hitbox.activate(a, facing)
		Sfx.play(a.sfx_whoosh, -4.0)
		_spawn_trail(a)
		if not a.air and not _enemy_in_front(22.0):
			velocity.x = facing * a.lunge
		elif a.id == &"air_spike":
			velocity.y = maxf(velocity.y, 120.0)
		if a.heavy and not a.air:
			Juice.dust(global_position + Vector2(facing * 40.0, 0.0), 8, facing)
	elif f == active_end + 1:
		hitbox.deactivate()

	_queue_followup(a)

	if f > active_end:
		if _queued != &"" and f > active_end + a.cancel_after:
			_start_attack(_queued)
			return
		# 收招可以被冲刺打断（闪避取消）
		if _buf[&"dash"] > 0.0 and _can_start_dash():
			_start_dash()
			return
		# 打中之后可以跳跃取消（上勾拳后跳起追击）
		if _attack_hit and _buf[&"jump"] > 0.0 and is_on_floor():
			_end_attack()
			_do_jump(false)
			return
	if f >= a.total_frames:
		_end_attack()


func _state_dash(delta: float) -> void:
	_dash_t -= delta
	velocity = Vector2(facing * dash_speed, 0.0)
	if _frame % 3 == 0:
		Juice.spawn(rig.make_ghost(), rig.global_position)
	if _dash_t <= 0.0:
		state = State.NORMAL
		velocity.x = facing * run_speed


func _state_hurt(delta: float) -> void:
	_hurt_t -= delta
	_apply_gravity(delta)
	velocity.x = move_toward(velocity.x, 0.0, 500.0 * delta)
	if _hurt_t <= 0.0:
		state = State.NORMAL


# ---------------------------------------------------------------- 动作

func _try_attack() -> bool:
	var air := not is_on_floor()
	if _buf[&"heavy"] > 0.0:
		_start_attack(&"air_spike" if air else &"power")
		return true
	if _buf[&"attack"] > 0.0:
		if air:
			_start_attack(&"air_kick1")
		elif Input.is_action_pressed(&"move_up"):
			_start_attack(&"uppercut")
		else:
			_start_attack(&"hc1")
		return true
	return false


func _queue_followup(a: AttackData) -> void:
	if _queued != &"":
		return
	if _buf[&"attack"] > 0.0:
		if not a.air and a.id != &"uppercut" and Input.is_action_pressed(&"move_up"):
			_queued = &"uppercut"
		elif a.next_combo != &"":
			_queued = a.next_combo
		else:
			return
		_buf[&"attack"] = 0.0
	elif _buf[&"heavy"] > 0.0:
		if a.air and a.id != &"air_spike":
			_queued = &"air_spike"
		elif a.id == &"hc1" or a.id == &"hc2":
			_queued = &"power"
		else:
			return
		_buf[&"heavy"] = 0.0


func _start_attack(id: StringName) -> void:
	_attack = attacks[id]
	_attack_frame = 0
	_queued = &""
	_attack_hit = false
	_buf[&"attack"] = 0.0
	_buf[&"heavy"] = 0.0
	hitbox.deactivate()
	var ix := Input.get_axis(&"move_left", &"move_right")
	if ix != 0.0:
		facing = 1 if ix > 0.0 else -1
	state = State.ATTACK


func _end_attack() -> void:
	hitbox.deactivate()
	_attack = null
	state = State.NORMAL


func _can_start_dash() -> bool:
	return can_dash and _dash_cd <= 0.0 and (is_on_floor() or not _air_dash_used)


func _start_dash() -> void:
	hitbox.deactivate()
	_attack = null
	_buf[&"dash"] = 0.0
	var ix := Input.get_axis(&"move_left", &"move_right")
	if ix != 0.0:
		facing = 1 if ix > 0.0 else -1
	if not is_on_floor():
		_air_dash_used = true
	_dash_t = dash_time
	_dash_cd = dash_cooldown
	state = State.DASH
	rig.squash = Vector2(1.3, 0.8)
	Sfx.play("dash", -6.0)
	Juice.dust(global_position, 4, -facing)


func _try_jump() -> void:
	if _buf[&"jump"] <= 0.0:
		return
	if is_on_floor() and Input.is_action_pressed(&"move_down") and _standing_on_one_way():
		_buf[&"jump"] = 0.0
		_drop_through()
	elif _coyote > 0.0:
		_do_jump(false)
	elif _air_jumps > 0:
		_air_jumps -= 1
		_do_jump(true)


func _do_jump(air: bool) -> void:
	_buf[&"jump"] = 0.0
	_coyote = 0.0
	_jump_held = true
	velocity.y = -jump_velocity * (0.9 if air else 1.0)
	rig.squash = Vector2(0.7, 1.3)
	rig.play_anim(&"jump", 1.0, true)
	Sfx.play("jump", -8.0)
	Juice.dust(global_position, 6 if air else 4)


func _apply_gravity(delta: float, mult := 1.0) -> void:
	if _jump_held and velocity.y < 0.0 and not Input.is_action_pressed(&"jump"):
		velocity.y *= jump_cut
		_jump_held = false
	if velocity.y >= 0.0:
		_jump_held = false
	var g := gravity * (fall_gravity_mult if velocity.y > 0.0 else 1.0) * mult
	velocity.y = minf(velocity.y + g * delta, max_fall_speed)


func _enemy_in_front(distance: float) -> bool:
	for e in get_tree().get_nodes_in_group(&"enemies"):
		var enemy := e as Enemy
		if enemy == null or enemy.state == Enemy.State.DEAD:
			continue
		var d := enemy.global_position - global_position
		if absf(d.y) < 30.0 and d.x * facing > 0.0 and absf(d.x) < distance:
			return true
	return false


func _standing_on_one_way() -> bool:
	for i in get_slide_collision_count():
		var block := get_slide_collision(i).get_collider() as Block
		if block and block.one_way:
			return true
	return false


func _drop_through() -> void:
	set_collision_mask_value(ONE_WAY_LAYER, false)
	velocity.y = 60.0
	get_tree().create_timer(0.25).timeout.connect(set_collision_mask_value.bind(ONE_WAY_LAYER, true))


# ---------------------------------------------------------------- 命中与受击

func _on_hit_landed(target: Hurtbox, _hit: HitData) -> void:
	_attack_hit = true
	if _attack and _attack.air:
		# 空中打中会"踩"一下，维持空中连段；同时返还空中冲刺
		velocity.y = minf(velocity.y, -150.0)
		_air_dash_used = false
		# 跟住被打的目标，空中连段不会越打越远
		var body := target.get_parent() as CharacterBody2D
		if body:
			velocity.x = body.velocity.x


func _on_hurt(hit: HitData) -> void:
	if state == State.DEAD:
		return
	health = maxi(health - hit.damage, 0)
	health_changed.emit(health, max_health)
	hitbox.deactivate()
	_attack = null
	velocity = hit.knockback
	facing = -hit.direction
	_invuln_t = invincible_time
	rig.flash(Color(1, 0.3, 0.3), 0.12)
	Sfx.play("hurt")
	if health <= 0:
		state = State.DEAD
		Juice.slowmo(0.3, 0.9)
		get_tree().create_timer(1.4).timeout.connect(_respawn)
	else:
		state = State.HURT
		rig.play_anim(&"hurt", 1.0, true)
		_hurt_t = hit.stagger


func _respawn() -> void:
	global_position = _spawn_pos
	reset_physics_interpolation()  # 瞬移，不要从死亡位置插值滑过来
	velocity = Vector2.ZERO
	health = max_health
	health_changed.emit(health, max_health)
	state = State.NORMAL
	_invuln_t = invincible_time


func is_alive() -> bool:
	return state != State.DEAD


# ---------------------------------------------------------------- 表现

func _tick_timers(delta: float) -> void:
	for action in _buf:
		_buf[action] = maxf(_buf[action] - delta, 0.0)
	_coyote -= delta
	_dash_cd -= delta
	_invuln_t -= delta
	_land_t -= delta
	hurtbox.invincible = _invuln_t > 0.0 or state == State.DASH or state == State.DEAD


func _after_move() -> void:
	var on_floor := is_on_floor()
	if on_floor and not _was_on_floor and _fall_speed > 150.0:
		rig.squash = Vector2(1.25, 0.75)
		_land_t = 0.12  # 落地蹲 3 帧 @24fps
		Juice.dust(global_position, 5)
		Sfx.play("land", -10.0)
	_was_on_floor = on_floor


func _update_rig(_delta: float) -> void:
	rig.facing = facing
	rig.tint_amount = 0.0
	match state:
		State.NORMAL:
			if not is_on_floor():
				rig.play_anim(&"jump" if velocity.y < 0.0 else &"fall")
			elif absf(velocity.x) > 20.0:
				rig.play_anim(&"run", clampf(absf(velocity.x) / run_speed, 0.6, 1.2))
			elif _land_t > 0.0:
				rig.play_anim(&"land")
			else:
				rig.play_anim(&"idle")
		State.ATTACK:
			var a := _attack
			if a:
				rig.show_attack(a.anim, _attack_frame, a.anim_timing, a.startup)
				if a.heavy and _attack_frame <= a.startup:  # 重击蓄力时发光，提示"要来了"
					rig.tint_amount = 0.5 * float(_attack_frame) / a.startup
		State.DASH:
			rig.play_anim(&"dash")
		State.HURT:
			rig.play_anim(&"hurt")
		State.DEAD:
			rig.play_anim(&"death")
	# 无敌闪烁
	var blink := _invuln_t > 0.0 and state != State.DASH and fmod(Time.get_ticks_msec() / 70.0, 2.0) < 1.0
	rig.modulate.a = 0.35 if blink else 1.0


func _spawn_trail(a: AttackData) -> void:
	if a.trail.z <= 0.0:
		return
	var t := SlashTrail.new()
	t.facing = facing
	t.from_deg = a.trail.x
	t.to_deg = a.trail.y
	t.radius = a.trail.z
	t.heavy = a.heavy
	t.width = 18.0 if a.heavy else 13.0
	Juice.spawn(t, global_position + Vector2(a.trail_center.x * facing, a.trail_center.y))
