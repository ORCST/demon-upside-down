@tool
class_name Block
extends StaticBody2D
## 灰盒地形块：原点在左上角，在编辑器里改 size 就能拉伸。
## one_way = 单向平台（可以从下面跳上去，按 下+跳 穿下来）。

@export var size := Vector2(64, 16):
	set(v):
		size = v
		_rebuild()
@export var one_way := false:
	set(v):
		one_way = v
		_rebuild()
@export var color := Color("2a2238"):
	set(v):
		color = v
		queue_redraw()
@export var top_color := Color("5a4a7a"):
	set(v):
		top_color = v
		queue_redraw()

var _shape: CollisionShape2D


func _ready() -> void:
	_rebuild()


func _rebuild() -> void:
	if not is_inside_tree():
		return
	if _shape == null:
		_shape = CollisionShape2D.new()
		add_child(_shape)
	var rect := RectangleShape2D.new()
	rect.size = Vector2(size.x, 6.0) if one_way else size
	_shape.shape = rect
	_shape.position = rect.size / 2.0
	_shape.one_way_collision = one_way
	collision_layer = 32 if one_way else 1
	collision_mask = 0
	queue_redraw()


func _draw() -> void:
	if one_way:
		draw_rect(Rect2(0, 0, size.x, 4), top_color)
		draw_rect(Rect2(0, 4, size.x, 2), color)
		for x in range(4, int(size.x), 12):
			draw_line(Vector2(x, 6), Vector2(x + 3, 12), color, 1.0)
		return
	draw_rect(Rect2(Vector2.ZERO, size), color)
	draw_rect(Rect2(0, 0, size.x, 3), top_color)
	var line := color.darkened(0.3)
	var row := 0
	for y in range(11, int(size.y), 8):
		draw_line(Vector2(0, y), Vector2(size.x, y), line, 1.0)
		var off := 8 if row % 2 == 0 else 0
		for x in range(off, int(size.x), 16):
			draw_line(Vector2(x, y - 8), Vector2(x, y), line, 1.0)
		row += 1
