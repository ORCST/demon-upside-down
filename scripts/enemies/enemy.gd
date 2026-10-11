class_name Enemy
extends CharacterBody2D
## 敌人基类：受击硬直、击飞、空中连段托举、撞墙/落地反弹、死亡慢动作、重生。
## 子类只需要实现 _act()（自己的 AI）和 _pose_act()（AI 状态下的姿势）。

signal defeated(enemy: Enemy)

enum State { ACT, HURT, LAUNCHED, DEAD }

@export var max_health := 60
@export var immortal := false
## 越重被打得越近
@export var weight := 1.0
@export var gravity := 950.0
@export var max_fall_speed := 520.0
@export var ground_friction := 900.0
@export var respawn_time := 3.0

var health := 0
var state := State.ACT
var facing := -1

var _hurt_t := 0.0
var _spawn_pos := Vector2.ZERO
var _pre_velocity := Vector2.ZERO
var _was_on_floor := true

@onready var rig: Puppet = $Rig
@onready var hurtbox: Hurtbox = $Hurtbox


func _ready() -> void:
	health = max_health
	_spawn_pos = global_position
	hurtbox.hurt.connect(_on_hurt)


func _physics_process(delta: float) -> void:
	match state:
		State.ACT:
			_act(delta)
		State.HURT:
			_hurt_t -= delta
			_fall(delta)
			_friction(delta)
			if _hurt_t <= 0.0 and is_on_floor():
				state = State.ACT
		State.LAUNCHED:
			_fall(delta, 0.75)
		State.DEAD:
			_fall(delta)
			if is_on_floor():
				_friction(delta, 0.4)
	_pre_velocity = velocity
	move_and_slide()
	_separate_from_player(delta)
	_check_impacts()
	_pose(delta)
	_was_on_floor = is_on_floor()


# ---------------------------------------------------------------- 子类覆盖

func _act(delta: float) -> void:
	_fall(delta)
	_friction(delta)


func _pose_act(_delta: float) -> void:
	pass


func _interrupt() -> void:
	pass


func _on_damaged(_hit: HitData) -> void:
	pass


# ---------------------------------------------------------------- 物理

func _fall(delta: float, mult := 1.0) -> void:
	velocity.y = minf(velocity.y + gravity * mult * delta, max_fall_speed)


func _friction(delta: float, mult := 1.0) -> void:
	velocity.x = move_toward(velocity.x, 0.0, ground_friction * mult * delta)


## 和玩家重叠时自己往外挪一点，避免两人叠在一起看不清
func _separate_from_player(delta: float) -> void:
	if state == State.DEAD:
		return
	var p := get_tree().get_first_node_in_group(&"player") as Node2D
	if p == null:
		return
	var d := global_position - p.global_position
	if absf(d.x) < 14.0 and absf(d.y) < 30.0:
		var dir := signf(d.x) if d.x != 0.0 else float(-facing)
		move_and_collide(Vector2(dir * 90.0 * delta, 0.0))


func _check_impacts() -> void:
	if state == State.ACT:
		return
	# 被打飞撞墙：反弹 + 小震
	if is_on_wall() and absf(_pre_velocity.x) > 220.0:
		velocity.x = -_pre_velocity.x * 0.45
		_impact_fx(global_position + Vector2(signf(_pre_velocity.x) * 8.0, -20.0), 0.3, Vector2(signf(_pre_velocity.x), 0))
	# 砸到地面：速度够快就弹起来（可以再接一套），否则倒地
	if is_on_floor() and not _was_on_floor and (state == State.LAUNCHED or state == State.DEAD):
		if _pre_velocity.y > 260.0:
			velocity.y = -_pre_velocity.y * 0.42
			_impact_fx(global_position, 0.3, Vector2.DOWN)
		elif state == State.LAUNCHED:
			state = State.HURT
			_hurt_t = 0.35
			Juice.dust(global_position, 4)


func _impact_fx(pos: Vector2, strength: float, dir: Vector2) -> void:
	Juice.hitstop(0.04)
	Juice.shake(strength, dir)
	Juice.dust(pos, 6)
	Sfx.play("bounce", -4.0)


# ---------------------------------------------------------------- 受击

func _on_hurt(hit: HitData) -> void:
	if state == State.DEAD:
		return
	health -= hit.damage
	if immortal:
		health = maxi(health, 1)
	facing = -hit.direction
	_interrupt()
	rig.flash(Color.WHITE, 0.09)

	var kb := hit.knockback / weight
	var juggled := state == State.LAUNCHED
	if juggled and kb.y <= 0.0 and not hit.launcher:
		kb.y = minf(kb.y, -170.0)  # 空中挨打：托住，方便空中连段
	elif not juggled and kb.y > -150.0 and kb.y <= 0.0:
		kb.y = 0.0                  # 地面轻击：只后退不离地
	velocity = kb
	_hurt_t = hit.stagger
	if hit.launcher or juggled or kb.y < -150.0 or kb.y > 0.0:
		state = State.LAUNCHED
	else:
		state = State.HURT
	_on_damaged(hit)
	if health <= 0:
		_die(hit)


func _die(hit: HitData) -> void:
	state = State.DEAD
	hurtbox.invincible = true
	velocity = Vector2(hit.knockback.x * 1.4, minf(hit.knockback.y, -220.0)) / weight
	Juice.hitstop(0.16)
	Juice.slowmo(0.25, 0.75)
	Juice.shake(0.7, Vector2(hit.direction, 0))
	Sfx.play("ko")
	rig.flash(Color.WHITE, 0.2)
	defeated.emit(self)
	await get_tree().create_timer(1.6).timeout
	var tw := create_tween()
	tw.tween_property(rig, "modulate:a", 0.0, 0.4)
	await tw.finished
	visible = false
	await get_tree().create_timer(respawn_time).timeout
	_respawn()


func _respawn() -> void:
	global_position = _spawn_pos
	velocity = Vector2.ZERO
	health = max_health
	state = State.ACT
	hurtbox.invincible = false
	visible = true
	rig.modulate.a = 1.0
	rig.flash(Color(0.6, 0.2, 1.0), 0.3)


# ---------------------------------------------------------------- 表现

func _pose(delta: float) -> void:
	rig.facing = facing
	rig.airborne = not is_on_floor()
	rig.fist = Vector2.ZERO
	rig.foot = Vector2.ZERO
	rig.fist_big = false
	rig.crouch = 0.0
	rig.tint_amount = 0.0
	rig.run_amount = 0.0
	match state:
		State.ACT:
			rig.lean = 0.0
			_pose_act(delta)
		State.HURT:
			rig.lean = -0.5
		State.LAUNCHED:
			rig.lean = -0.9
		State.DEAD:
			rig.lean = -1.4
			rig.crouch = 1.0
