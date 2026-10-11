class_name Dust
extends Node2D
## 落地 / 起跳 / 冲刺时的尘土小团。dir = 0 时向两边散开，否则往 dir 方向。

var amount := 5
var dir := 0.0
var life := 0.35

var _t := 0.0
var _puffs: Array[Dictionary] = []


func _ready() -> void:
	z_index = 20
	for i in amount:
		var side := dir if dir != 0.0 else (1.0 if i % 2 == 0 else -1.0)
		_puffs.append({
			"pos": Vector2(randf_range(-3, 3), randf_range(-2, 0)),
			"vel": Vector2(side * randf_range(25, 70), randf_range(-25, -5)),
			"r": randf_range(2.0, 3.5),
		})


func _process(delta: float) -> void:
	_t += delta
	if _t >= life:
		queue_free()
		return
	for p in _puffs:
		p.pos += p.vel * delta
		p.vel *= 1.0 - 6.0 * delta
	queue_redraw()


func _draw() -> void:
	var k := _t / life
	for p in _puffs:
		draw_circle(p.pos, p.r * (1.0 + k), Color(0.85, 0.82, 0.9, 0.8 * (1.0 - k)))
