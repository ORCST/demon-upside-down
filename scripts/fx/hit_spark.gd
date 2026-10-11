class_name HitSpark
extends Node2D
## 命中火花：白色闪光 + 放射线（重击再加冲击环）。
## 顿帧时会停在第一帧，形成"定格的冲击画面"。

var dir := Vector2.RIGHT
var heavy := false
var life := 0.16

var _t := 0.0
var _rays: Array[Vector2] = []  # x = 角度, y = 长度


func _ready() -> void:
	z_index = 50
	if heavy:
		life = 0.22
	var n := 8 if heavy else 5
	for i in n:
		var ang := dir.angle() + randf_range(-1.2, 1.2)
		if i == n - 1:
			ang += PI  # 一根往回炸，更有冲击感
		_rays.append(Vector2(ang, randf_range(10.0, 20.0) * (1.7 if heavy else 1.0)))


func _process(delta: float) -> void:
	_t += delta
	if _t >= life:
		queue_free()
	queue_redraw()


func _draw() -> void:
	var k := clampf(_t / life, 0.0, 1.0)
	if k < 0.4:
		draw_circle(Vector2.ZERO, (9.0 if heavy else 5.0) * (1.0 - k), Color.WHITE)
	var col := Color(1.0, 0.95, 0.65, 1.0 - k)
	for r in _rays:
		var v := Vector2.from_angle(r.x)
		draw_line(v * r.y * k * 0.6, v * r.y * (0.35 + k), col, 2.0 if heavy else 1.0)
	if heavy:
		draw_arc(Vector2.ZERO, 6.0 + 28.0 * k, 0.0, TAU, 24, Color(1, 1, 1, 1.0 - k), 2.0)
