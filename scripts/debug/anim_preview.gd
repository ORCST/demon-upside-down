extends Node2D
## 动画预览：把 SpriteFrames 里的每个动画并排循环播放，下面标名字。
## 直接运行 scenes/debug/anim_preview.tscn；一次性动作播完会停一下再重播。

@export var frames: SpriteFrames = preload("res://assets/sprites/niulai/niulai.tres")
@export var spacing := 150.0
@export var ground_y := 250.0

var _sprites: Array[AnimatedSprite2D] = []


func _ready() -> void:
	var names := frames.get_animation_names()
	var start_x := 320.0 - spacing * (names.size() - 1) / 2.0
	for i in names.size():
		var s := AnimatedSprite2D.new()
		s.sprite_frames = frames
		s.animation = names[i]
		s.centered = false
		s.offset = Vector2(-112, -208)  # 标准画布上的脚底锚点
		s.position = Vector2(start_x + i * spacing, ground_y)
		add_child(s)
		s.play()
		s.animation_finished.connect(_replay.bind(s))
		_sprites.append(s)
		var label := Label.new()
		label.text = "%s (%d)" % [names[i], frames.get_frame_count(names[i])]
		label.position = s.position + Vector2(-40, 8)
		label.add_theme_font_size_override(&"font_size", 10)
		add_child(label)


func _draw() -> void:
	draw_line(Vector2(0, ground_y), Vector2(640, ground_y), Color("5a4a7a"), 1.0)


func _replay(s: AnimatedSprite2D) -> void:
	await get_tree().create_timer(0.5).timeout
	s.frame = 0
	s.play()
