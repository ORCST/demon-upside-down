class_name NiulaiSprite
extends Node2D
## 牛来的精灵显示（替代主角的几何木偶）。原点在脚底，所有动画共用 256 画布锚点 (112, 208)。
## 循环动画（idle/run）自己播放；攻击帧由玩家脚本按招式帧数逐帧指定，顿帧时自然定格。

const FLASH_SHADER := preload("res://shaders/hit_flash.gdshader")
const FRAMES := preload("res://assets/sprites/niulai3d/niulai3d.tres")
const ANCHOR := Vector2(-112, -208)

var facing := 1
var squash := Vector2.ONE   ## 挤压拉伸，会自动弹回 1
var tint := Color(1, 0.85, 0.3)
var tint_amount := 0.0
var is_ghost := false

var _sprite := AnimatedSprite2D.new()
var _flash_t := 0.0
var _flash_color := Color.WHITE
var _mat: ShaderMaterial


func _ready() -> void:
	_sprite.sprite_frames = FRAMES
	_sprite.centered = false
	_sprite.offset = ANCHOR
	_sprite.use_parent_material = true
	add_child(_sprite)
	if not is_ghost:
		_mat = ShaderMaterial.new()
		_mat.shader = FLASH_SHADER
		material = _mat
		play_anim(&"idle")


## 自动播放的动画（idle / run / jump / fall / dash / hurt ...）；是否循环由资源决定，单次动画播完停在最后一帧。
## restart=true 时从头重播（二段跳、连续受击）
func play_anim(anim: StringName, speed := 1.0, restart := false) -> void:
	if restart or _sprite.animation != anim or (not _sprite.is_playing() and FRAMES.get_animation_loop(anim)):
		_sprite.play(anim)
		_sprite.frame = 0
	_sprite.speed_scale = speed


## 攻击：timing 是每帧持续的物理帧数；为空时按"出招前第 0 帧、之后第 1 帧"显示
func show_attack(anim: StringName, attack_frame: int, timing: PackedInt32Array, startup: int) -> void:
	var count := FRAMES.get_frame_count(anim)
	var index := 0
	if timing.is_empty():
		index = 0 if attack_frame <= startup else mini(1, count - 1)
	else:
		var t := attack_frame
		while index < timing.size() - 1 and t > timing[index]:
			t -= timing[index]
			index += 1
	_sprite.animation = anim
	_sprite.stop()
	_sprite.frame = mini(index, count - 1)


func flash(color := Color.WHITE, duration := 0.1) -> void:
	_flash_color = color
	_flash_t = duration


func make_ghost() -> NiulaiSprite:
	var g := NiulaiSprite.new()
	g.is_ghost = true
	g.facing = facing
	g.squash = squash
	g.modulate = Color(0.45, 0.85, 1.0, 0.55)
	g.z_index = z_index - 1
	g.ready.connect(func() -> void:
		g._sprite.animation = _sprite.animation
		g._sprite.frame = _sprite.frame
		g._sprite.stop())
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
