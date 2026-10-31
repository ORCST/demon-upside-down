extends Node2D
## 城堡大厅背景（C 卡通风格）。从后往前五层视差，都水平无限平铺：
##   夜空（从窗洞透出）→ 后墙（墙面/拱窗/柱子/旗帜/火把）→ 吊灯铁链 →（游戏层）→ 前景剪影。
## 素材在 assets/environment/castle_c/（由 Codex 按 docs/计划/2026-10-29_城堡C风格场景素材需求.md 整理）。
## 竖直方向跟世界锁定，墙脚贴着地面 floor_y。

const DIR := "res://assets/environment/castle_c/"
const WALL_H := 384
## 后墙一组 6 个模块（每个 128px），之后重复
const WALL_MODULES := ["wall_window", "wall_plain", "wall_window_small", "wall_plain", "wall_window", "wall_plain"]
const COLUMNS_X := [104, 616]            ## 柱子左边缘
const BANNERS_X := [424, 680]            ## 旗帜左边缘（挂在素墙上）
const TORCHES_X := [128, 244, 396, 640]  ## 火把中心
const TORCH_Y := 168                     ## 火把中心在地面以上的高度

@export var floor_y := 300.0
@export var sky_scroll := 0.25
@export var back_scroll := 0.55
@export var chain_scroll := 0.8
@export var front_scroll := 1.3

var _glows: Array[Sprite2D] = []
var _t := 0.0


func _ready() -> void:
	var wall_top := floor_y - WALL_H
	var sky := _layer(sky_scroll, 640.0)
	_sprite(sky, "sky_far", Vector2(0, wall_top))

	var back := _layer(back_scroll, 128.0 * WALL_MODULES.size())
	for i in WALL_MODULES.size():
		_sprite(back, WALL_MODULES[i], Vector2(128 * i, wall_top))
	for x in COLUMNS_X:
		_sprite(back, "column", Vector2(x, wall_top))
	for x in BANNERS_X:
		_sprite(back, "banner", Vector2(x, wall_top + 36))
	var torch_frames := _torch_frames()
	var glow_tex := _glow_texture()
	for x in TORCHES_X:
		var pos := Vector2(x, floor_y - TORCH_Y)
		var t := AnimatedSprite2D.new()
		t.sprite_frames = torch_frames
		t.position = pos
		t.play(&"burn")
		t.frame = randi() % 4  # 不让所有火把同步跳动
		back.add_child(t)
		var g := Sprite2D.new()
		g.texture = glow_tex
		g.position = pos + Vector2(0, -10)
		g.material = CanvasItemMaterial.new()
		(g.material as CanvasItemMaterial).blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		back.add_child(g)
		_glows.append(g)

	# 一盏挂灯：铁链从画面顶上垂下来
	var mid := _layer(chain_scroll, 960.0)
	var lantern_top := floor_y - 236.0
	var chain: Texture2D = load(DIR + "chain.png")
	var y := lantern_top - chain.get_height()
	while y > floor_y - 560.0:
		_sprite(mid, "chain", Vector2(574, y))
		y -= chain.get_height()
	_sprite(mid, "lantern", Vector2(560, lantern_top))

	# 前景剪影：比镜头移动得快，挡在角色前面，分得很开免得遮挡战斗
	var front := _layer(front_scroll, 1400.0)
	front.z_index = 30
	_sprite(front, "fg_fence", Vector2(40, floor_y + 100 - 160))
	_sprite(front, "fg_pillar", Vector2(820, floor_y + 80 - 360))


func _process(delta: float) -> void:
	_t += delta
	for i in _glows.size():
		var f := 0.85 + 0.1 * sin(_t * 9.0 + i * 1.7) + 0.05 * sin(_t * 23.0 + i)
		_glows[i].modulate = Color(1, 1, 1, f)
		_glows[i].scale = Vector2.ONE * (0.95 + 0.08 * f)


func _layer(scroll: float, repeat_x: float) -> Parallax2D:
	var p := Parallax2D.new()
	p.scroll_scale = Vector2(scroll, 1.0)
	p.repeat_size = Vector2(repeat_x, 0)
	p.repeat_times = 4
	add_child(p)
	return p


func _sprite(parent: Node, file: String, pos: Vector2) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = load(DIR + file + ".png")
	s.centered = false
	s.position = pos
	parent.add_child(s)
	return s


func _torch_frames() -> SpriteFrames:
	var sheet: Texture2D = load(DIR + "torch.png")
	var frames := SpriteFrames.new()
	frames.add_animation(&"burn")
	frames.set_animation_speed(&"burn", 7.0)
	for i in 4:
		var a := AtlasTexture.new()
		a.atlas = sheet
		a.region = Rect2(24 * i, 0, 24, 48)
		frames.add_frame(&"burn", a)
	frames.remove_animation(&"default")
	return frames


func _glow_texture() -> GradientTexture2D:
	var g := Gradient.new()
	g.colors = PackedColorArray([Color(1.0, 0.62, 0.25, 0.5), Color(1.0, 0.45, 0.15, 0.0)])
	var t := GradientTexture2D.new()
	t.gradient = g
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	t.width = 64
	t.height = 64
	return t
