extends Node2D
## 远景：月亮 + 哥特城堡剪影，放在 Parallax2D 里慢速滚动。占位用。

@export var width := 2200.0
@export var ground_y := 330.0


func _draw() -> void:
	draw_circle(Vector2(520, 70), 26.0, Color("e8dcc0"))
	var far := Color("2b2140")
	var near := Color("1f1830")
	_skyline(far, 140.0, 37)
	_skyline(near, 190.0, 91)


func _skyline(col: Color, base_h: float, seed_value: int) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	var x := -100.0
	while x < width:
		var w := rng.randf_range(30, 80)
		var h := base_h + rng.randf_range(-40, 60)
		draw_rect(Rect2(x, ground_y - h, w, h), col)
		if rng.randf() < 0.5:
			# 尖塔
			draw_colored_polygon(PackedVector2Array([
				Vector2(x + w * 0.2, ground_y - h), Vector2(x + w * 0.5, ground_y - h - rng.randf_range(20, 50)),
				Vector2(x + w * 0.8, ground_y - h)]), col)
		if rng.randf() < 0.35:
			draw_rect(Rect2(x + w * 0.4, ground_y - h + 14, 4, 6), Color("ffcf6a", 0.5))
		x += w + rng.randf_range(0, 20)
