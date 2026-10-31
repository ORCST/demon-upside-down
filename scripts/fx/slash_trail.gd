class_name SlashTrail
extends Node2D
## 刀光：沿挥砍方向的一道月牙。角度以"朝右"为准（y 向下，0 = 正前方，90 = 正下方），
## 由 facing 翻转。顿帧时随时间缩放一起定格。

var facing := 1
var from_deg := 180.0
var to_deg := 20.0
var radius := 55.0
var width := 14.0
var heavy := false
var life := 0.14

var _t := 0.0


func _ready() -> void:
	z_index = 45
	scale.x = facing
	if heavy:
		life = 0.2


func _process(delta: float) -> void:
	_t += delta
	if _t >= life:
		queue_free()
	queue_redraw()


func _draw() -> void:
	var k := clampf(_t / life, 0.0, 1.0)
	var steps := 18
	# 月牙前端最宽、尾端变细；整体从尾部开始消失
	var start := lerpf(0.0, 0.85, k)
	var outer := PackedVector2Array()
	var inner := PackedVector2Array()
	for i in steps + 1:
		var u := lerpf(start, 1.0, float(i) / steps)
		var ang := deg_to_rad(lerpf(from_deg, to_deg, u))
		var w := width * u * (1.0 - k * 0.6)
		outer.append(Vector2.from_angle(ang) * radius)
		inner.append(Vector2.from_angle(ang) * (radius - w))
	inner.reverse()
	var poly := outer + inner
	if poly.size() >= 3:
		draw_colored_polygon(poly, Color(1.0, 1.0, 0.92, 0.9 * (1.0 - k)))
	draw_polyline(outer, Color(1.0, 0.85, 0.45, 1.0 - k), 2.0 if heavy else 1.0)
