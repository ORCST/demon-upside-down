extends CanvasLayer
## 界面：左上血量、右侧连击数、底部操作提示。

const HINT := "A/D 移动  K 跳(二段跳)  J 大剑(连按三刀)  U 重击  W+J 上挑  空中 J/U  L 冲刺   F1 判定框  R 重来"

var _pips: Pips
var _combo_label: Label
var _dmg_label: Label
var _combo := 0
var _damage := 0
var _combo_t := 0.0


class Pips:
	extends Control
	var current := 6
	var maximum := 6

	func _draw() -> void:
		for i in maximum:
			var r := Rect2(i * 12, 0, 9, 9)
			draw_rect(r.grow(1), Color("120d1a"))
			draw_rect(r, Color("e04a5a") if i < current else Color("3a2a40"))


func _ready() -> void:
	layer = 10
	_pips = Pips.new()
	_pips.position = Vector2(12, 12)
	add_child(_pips)

	_combo_label = _label(28, Color("ffe08a"))
	_combo_label.position = Vector2(500, 60)
	_combo_label.size = Vector2(128, 32)
	_combo_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_dmg_label = _label(10, Color("f0e6ff"))
	_dmg_label.position = Vector2(500, 92)
	_dmg_label.size = Vector2(128, 14)
	_dmg_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT

	var hint := _label(10, Color(1, 1, 1, 0.75))
	hint.text = HINT
	hint.position = Vector2(8, 344)

	Juice.hit_landed.connect(_on_hit)
	Juice.player_hurt.connect(func(_h: HitData) -> void: _combo_t = 0.0)
	_hook_player.call_deferred()


func _hook_player() -> void:
	var p := get_tree().get_first_node_in_group(&"player") as Player
	if p:
		p.health_changed.connect(_on_health)
		_on_health(p.health, p.max_health)


func _process(delta: float) -> void:
	if _combo_t > 0.0:
		_combo_t -= delta
		if _combo_t <= 0.0:
			_combo = 0
			_damage = 0
	_combo_label.visible = _combo >= 2
	_dmg_label.visible = _combo >= 2
	_combo_label.scale = _combo_label.scale.lerp(Vector2.ONE, 1.0 - exp(-delta * 18.0))


func _on_hit(hit: HitData) -> void:
	_combo += 1
	_damage += hit.damage
	_combo_t = 1.4
	_combo_label.text = "%d HITS" % _combo
	_dmg_label.text = "%d DMG" % _damage
	_combo_label.pivot_offset = _combo_label.size * Vector2(1.0, 0.5)
	_combo_label.scale = Vector2(1.5, 1.5) if hit.heavy else Vector2(1.25, 1.25)


func _on_health(current: int, maximum: int) -> void:
	_pips.current = current
	_pips.maximum = maximum
	_pips.queue_redraw()


func _label(font_size: int, color: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override(&"font_size", font_size)
	l.add_theme_color_override(&"font_color", color)
	l.add_theme_color_override(&"font_outline_color", Color("120d1a"))
	l.add_theme_constant_override(&"outline_size", 4)
	add_child(l)
	return l
