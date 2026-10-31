extends Node
## 打击感中心（自动加载为 Juice）：顿帧、慢动作、震屏、手柄震动、命中特效。
## 所有"打中了"的反馈都从 impact() 统一出去，调手感只需要改 AttackData 里的数值。

signal hit_landed(hit: HitData)   ## 玩家打中敌人
signal player_hurt(hit: HitData)  ## 玩家被打中

## 顿帧时的时间缩放。不用 0：要靠它反推真实帧时间（录屏的固定帧率下也准确）。
const FROZEN_SCALE := 0.0001

var camera: GameCamera
var debug_draw := false
## 不受 time_scale 影响的本帧真实时长，震屏等"冻结时也要动"的东西用它
var real_delta := 0.0

var _clock := 0.0
var _applied_scale := 1.0
var _hitstop_end := 0.0
var _slowmo_end := 0.0
var _slowmo_scale := 1.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	process_priority = -1000  # 每帧最先运行，保证本帧 real_delta 已算好


func _process(delta: float) -> void:
	# 本帧的 delta 是按上一帧设定的缩放算出来的，只有这里会改 time_scale
	real_delta = delta / _applied_scale
	_clock += real_delta
	var target := 1.0
	if _clock < _slowmo_end:
		target = _slowmo_scale
	if _clock < _hitstop_end:
		target = FROZEN_SCALE
	if target != _applied_scale:
		_applied_scale = target
		Engine.time_scale = target


func hitstop(duration: float) -> void:
	if duration > 0.0:
		_hitstop_end = maxf(_hitstop_end, _clock + duration)


func slowmo(time_scale: float, duration: float) -> void:
	_slowmo_scale = time_scale
	_slowmo_end = maxf(_slowmo_end, _clock + duration)


func shake(amount: float, dir := Vector2.ZERO) -> void:
	if is_instance_valid(camera):
		camera.add_trauma(amount, dir)


func rumble(weak: float, strong: float, duration: float) -> void:
	for id in Input.get_connected_joypads():
		Input.start_joy_vibration(id, weak, strong, duration)


## 一次命中的全套反馈
func impact(hit: HitData) -> void:
	hitstop(hit.hitstop)
	shake(hit.shake, Vector2(hit.direction, 0))
	Sfx.play(hit.sfx)
	spark(hit.position, Vector2(hit.direction, 0), hit.heavy)
	if hit.heavy:
		rumble(0.4, 0.9, 0.2)
	else:
		rumble(0.6, 0.2, 0.08)
	if hit.by_player:
		hit_landed.emit(hit)
	else:
		player_hurt.emit(hit)


func spawn(node: Node2D, pos: Vector2) -> void:
	var scene := get_tree().current_scene
	if scene == null:
		node.free()
		return
	scene.add_child(node)
	node.global_position = pos
	node.reset_physics_interpolation()


func spark(pos: Vector2, dir: Vector2, heavy := false) -> void:
	var s := HitSpark.new()
	s.dir = dir
	s.heavy = heavy
	spawn(s, pos)
	_debris(pos, dir, 10 if heavy else 5)


func dust(pos: Vector2, amount := 5, dir := 0.0) -> void:
	var d := Dust.new()
	d.amount = amount
	d.dir = dir
	spawn(d, pos)


func _debris(pos: Vector2, dir: Vector2, amount: int) -> void:
	var p := CPUParticles2D.new()
	p.one_shot = true
	p.explosiveness = 1.0
	p.amount = amount
	p.lifetime = 0.35
	p.direction = dir
	p.spread = 55.0
	p.initial_velocity_min = 90.0
	p.initial_velocity_max = 220.0
	p.gravity = Vector2(0, 700)
	p.damping_min = 80.0
	p.damping_max = 160.0
	p.scale_amount_min = 1.0
	p.scale_amount_max = 2.5
	p.color = Color(1.0, 0.92, 0.7)
	p.z_index = 40
	spawn(p, pos)
	p.emitting = true
	get_tree().create_timer(0.6).timeout.connect(p.queue_free)
