class_name GameCamera
extends Camera2D
## 跟随相机：朝向前瞻 + 创伤值震屏 + 方向性"踢镜"。
## 跟随在物理帧里做（和角色一起被物理插值，高刷新率显示器上不会和角色错拍发糊）；
## 震屏用真实时间在渲染帧里算，所以顿帧冻结时画面仍在抖。

@export var target: Node2D
@export var look_ahead := 36.0
@export var vertical_offset := -40.0
@export var max_shake := 9.0
@export var shake_decay := 1.8

var _trauma := 0.0
var _kick := Vector2.ZERO


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Juice.camera = self
	process_callback = Camera2D.CAMERA2D_PROCESS_PHYSICS
	position_smoothing_enabled = true
	position_smoothing_speed = 7.0
	if target:
		global_position = _desired()
		reset_smoothing()
		reset_physics_interpolation()


func _physics_process(_delta: float) -> void:
	if is_instance_valid(target):
		global_position = _desired()


func _process(_delta: float) -> void:
	var rd := Juice.real_delta
	_trauma = maxf(_trauma - shake_decay * rd, 0.0)
	_kick = _kick.lerp(Vector2.ZERO, 1.0 - exp(-rd * 20.0))
	var s := _trauma * _trauma
	offset = (Vector2(randf_range(-1, 1), randf_range(-1, 1)) * max_shake * s + _kick).round()


func add_trauma(amount: float, dir := Vector2.ZERO) -> void:
	_trauma = minf(_trauma + amount, 1.0)
	_kick += dir * amount * 8.0


func _desired() -> Vector2:
	var f := 0
	if "facing" in target:
		f = target.facing
	return target.global_position + Vector2(f * look_ahead, vertical_offset)
