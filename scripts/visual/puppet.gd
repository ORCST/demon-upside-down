class_name Puppet
extends Node2D
## 占位角色"木偶"：用几何图形画出人物和动作姿势，原点在脚底。
## 之后换成 H3 生成的像素精灵时，只替换这个节点；玩家和敌人的逻辑不用动。
## 姿势参数都以"朝右"为准，由 facing 统一翻转。

enum Kind { HUMAN, DEMON, SANDBAG }

const FLASH_SHADER := preload("res://shaders/hit_flash.gdshader")

@export var kind := Kind.HUMAN
@export var skin := Color("f2c79b")
@export var shirt := Color("3d7be0")
@export var pants := Color("2b2d42")
@export var hair := Color("2b1d14")
@export var eye := Color("1a1a1a")

var facing := 1
var lean := 0.0           ## 身体前倾（弧度），负数为后仰
var crouch := 0.0         ## 下蹲 0..1
var airborne := false
var run_phase := 0.0
var run_amount := 0.0
var fist := Vector2.ZERO  ## 前手拳头位置，ZERO = 护架姿势
var fist_big := false
var foot := Vector2.ZERO  ## 前脚位置，ZERO = 正常站立
var squash := Vector2.ONE ## 挤压拉伸，会自动弹回 1
var tint := Color(1, 0.25, 0.2)
var tint_amount := 0.0    ## 持续染色（蓄力、前摇警告）
var is_ghost := false     ## 冲刺残影

var _flash_t := 0.0
var _flash_color := Color.WHITE
var _mat: ShaderMaterial


func _ready() -> void:
	if not is_ghost:
		_mat = ShaderMaterial.new()
		_mat.shader = FLASH_SHADER
		material = _mat


func flash(color := Color.WHITE, duration := 0.1) -> void:
	_flash_color = color
	_flash_t = duration


func make_ghost() -> Puppet:
	var g := Puppet.new()
	for p in ["kind", "skin", "shirt", "pants", "hair", "eye", "facing", "lean", "crouch",
			"airborne", "run_phase", "run_amount", "fist", "fist_big", "foot", "squash"]:
		g.set(p, get(p))
	g.is_ghost = true
	g.modulate = Color(0.45, 0.85, 1.0, 0.55)
	g.z_index = z_index - 1
	return g


func _process(delta: float) -> void:
	squash = squash.lerp(Vector2.ONE, 1.0 - exp(-delta * 16.0))
	scale = Vector2(facing * squash.x, squash.y)
	if is_ghost:
		modulate.a -= delta * 3.5
		if modulate.a <= 0.0:
			queue_free()
	elif _mat:
		var amount := tint_amount
		var col := tint
		if _flash_t > 0.0:
			_flash_t -= delta
			amount = 1.0
			col = _flash_color
		_mat.set_shader_parameter(&"flash_color", col)
		_mat.set_shader_parameter(&"flash_amount", amount)
	queue_redraw()


func _draw() -> void:
	if kind == Kind.SANDBAG:
		_draw_sandbag()
	else:
		_draw_fighter()


func _draw_fighter() -> void:
	var hip := Vector2(0, -19 + crouch * 6.0)
	var up := Vector2(sin(lean), -cos(lean))
	var neck := hip + up * 17.0
	var head := neck + up * 7.0 + Vector2(1, 0)
	var shoulder := hip + up * 14.0
	var swing := sin(run_phase) * run_amount

	# 腿
	var back_foot: Vector2
	var front_foot: Vector2
	if airborne:
		back_foot = hip + Vector2(-5, 13)
		front_foot = hip + Vector2(5, 10)
	else:
		back_foot = Vector2(-4 - swing * 9.0 - crouch * 3.0, -maxf(0.0, -cos(run_phase)) * 4.0 * run_amount)
		front_foot = Vector2(5 + swing * 9.0 + crouch * 3.0, -maxf(0.0, cos(run_phase)) * 4.0 * run_amount)
	if foot != Vector2.ZERO:
		front_foot = foot
	_limb(hip, back_foot, pants.darkened(0.3), 5.0)
	if foot == Vector2.ZERO:
		_limb(hip, front_foot, pants, 5.0)

	# 后手
	var back_fist := shoulder + Vector2(5 - swing * 6.0, 4)
	_limb(shoulder, back_fist, skin.darkened(0.25), 4.0)
	_fist_at(back_fist, 3.0, skin.darkened(0.25))

	# 躯干和头
	draw_line(hip, neck, shirt, 11.0)
	draw_circle(hip, 5.5, pants)
	draw_circle(head, 6.5, skin)
	if kind == Kind.DEMON:
		draw_colored_polygon(PackedVector2Array([head + Vector2(-5, -3), head + Vector2(-2, -5), head + Vector2(-6, -11)]), hair)
		draw_colored_polygon(PackedVector2Array([head + Vector2(2, -5), head + Vector2(5, -3), head + Vector2(6, -12)]), hair)
		draw_rect(Rect2(head + Vector2(2, -2), Vector2(3, 2)), eye)
	else:
		draw_arc(head, 6.0, PI * 0.9, PI * 2.05, 10, hair, 4.0)
		draw_rect(Rect2(head + Vector2(3, -2), Vector2(2, 2)), eye)

	# 踢腿时前腿画在躯干前面
	if foot != Vector2.ZERO:
		_limb(hip, front_foot, pants, 6.0)
		_fist_at(front_foot, 3.0, pants.darkened(0.4))

	# 前手
	var front_fist := fist if fist != Vector2.ZERO else shoulder + Vector2(9 + swing * 6.0, 1)
	_limb(shoulder, front_fist, skin, 4.0)
	_fist_at(front_fist, 4.5 if fist_big else 3.0, skin)


func _draw_sandbag() -> void:
	draw_rect(Rect2(-9, -3, 18, 3), Color("3a3046"))
	var up := Vector2(sin(lean), -cos(lean))
	var base := Vector2(0, -3)
	var top := base + up * 40.0
	draw_line(base + up * 4.0, top, shirt, 18.0)
	draw_circle(top, 9.0, shirt)
	for t in [0.3, 0.75]:
		var p: Vector2 = base.lerp(top, t)
		var side := Vector2(-up.y, up.x) * 9.0
		draw_line(p - side, p + side, pants, 2.0)
	var face := base.lerp(top, 0.9)
	for dx in [-3.0, 3.0]:
		var c := face + Vector2(dx + 1.0, 0)
		draw_line(c + Vector2(-1.5, -1.5), c + Vector2(1.5, 1.5), eye, 1.0)
		draw_line(c + Vector2(-1.5, 1.5), c + Vector2(1.5, -1.5), eye, 1.0)


func _limb(a: Vector2, b: Vector2, col: Color, width: float) -> void:
	draw_line(a, b, col, width)
	draw_circle(b, width * 0.5, col)


func _fist_at(p: Vector2, r: float, col: Color) -> void:
	draw_rect(Rect2(p - Vector2(r, r), Vector2(r, r) * 2.0), col)
