@tool
class_name Block
extends StaticBody2D
## 地形块：原点在左上角，在编辑器里改 size 就能拉伸。
## one_way = 单向平台（可以从下面跳上去，按 下+跳 穿下来）。
## 外观用城堡 C 风格贴图：实心块 = 亮色顶沿 + 石砖墙体 + 左右收边，单向平台 = 三段式木板
## （素材见 assets/environment/castle_c/）。

const TOP := preload("res://assets/environment/castle_c/floor_top.png")
const BODY := preload("res://assets/environment/castle_c/floor_body.png")
const EDGE_L := preload("res://assets/environment/castle_c/floor_edge_left.png")
const EDGE_R := preload("res://assets/environment/castle_c/floor_edge_right.png")
const PLANK := preload("res://assets/environment/castle_c/plank.png")
const PLANK_END := 12   ## 木板左右端宽度，中段 16px 重复
const EDGE_W := 16
const EDGE_TOP := 16    ## 收边图上面 16px 是顶沿，下面是可重复的墙体

@export var size := Vector2(64, 16):
	set(v):
		size = v
		_rebuild()
@export var one_way := false:
	set(v):
		one_way = v
		_rebuild()

var _shape: CollisionShape2D


func _ready() -> void:
	texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
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
		_draw_plank()
		return
	var top_h := minf(TOP.get_height(), size.y)
	draw_texture_rect(BODY, Rect2(0, top_h, size.x, size.y - top_h), true)
	draw_texture_rect(TOP, Rect2(0, 0, size.x, top_h), true)
	if size.x >= EDGE_W * 2:
		_draw_edge(EDGE_L, 0.0)
		_draw_edge(EDGE_R, size.x - EDGE_W)


func _draw_edge(tex: Texture2D, x: float) -> void:
	var top_h := minf(EDGE_TOP, size.y)
	draw_texture_rect_region(tex, Rect2(x, 0, EDGE_W, top_h), Rect2(0, 0, EDGE_W, top_h))
	var body_h := tex.get_height() - EDGE_TOP
	var y := top_h
	while y < size.y:
		var h := minf(body_h, size.y - y)
		draw_texture_rect_region(tex, Rect2(x, y, EDGE_W, h), Rect2(0, EDGE_TOP, EDGE_W, h))
		y += h


func _draw_plank() -> void:
	var h := PLANK.get_height()
	var mid := PLANK.get_width() - PLANK_END * 2
	draw_texture_rect_region(PLANK, Rect2(0, 0, PLANK_END, h), Rect2(0, 0, PLANK_END, h))
	var x := float(PLANK_END)
	while x < size.x - PLANK_END:
		var w := minf(mid, size.x - PLANK_END - x)
		draw_texture_rect_region(PLANK, Rect2(x, 0, w, h), Rect2(PLANK_END, 0, w, h))
		x += w
	draw_texture_rect_region(PLANK, Rect2(size.x - PLANK_END, 0, PLANK_END, h), Rect2(PLANK_END + mid, 0, PLANK_END, h))
