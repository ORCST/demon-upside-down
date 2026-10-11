class_name Hitbox
extends Area2D
## 攻击判定框。activate() 之后每个物理帧检查重叠的 Hurtbox，一次出招对同一目标只结算一次。

signal landed(target: Hurtbox, hit: HitData)

@export var by_player := false

var attack: AttackData
var facing := 1

var _active := false
var _already_hit: Array[Hurtbox] = []
var _shape := CollisionShape2D.new()
var _rect := RectangleShape2D.new()


func _ready() -> void:
	monitorable = false
	monitoring = false
	_shape.shape = _rect
	add_child(_shape)


func activate(a: AttackData, dir: int) -> void:
	attack = a
	facing = dir
	_already_hit.clear()
	_rect.size = a.hitbox_size
	_shape.position = Vector2(a.hitbox_offset.x * dir, a.hitbox_offset.y)
	_active = true
	set_deferred(&"monitoring", true)


func deactivate() -> void:
	_active = false
	set_deferred(&"monitoring", false)


func _physics_process(_delta: float) -> void:
	queue_redraw()
	if not _active or not monitoring:  # monitoring 是延迟打开的，第一帧可能还没生效
		return
	for area in get_overlapping_areas():
		var hurt := area as Hurtbox
		if hurt == null or _already_hit.has(hurt):
			continue
		_already_hit.append(hurt)
		var hit := _make_hit(hurt)
		if hurt.receive(hit):
			Juice.impact(hit)
			landed.emit(hurt, hit)


func _make_hit(hurt: Hurtbox) -> HitData:
	var h := HitData.new()
	h.damage = attack.damage
	h.knockback = Vector2(attack.knockback.x * facing, attack.knockback.y)
	h.hitstop = attack.hitstop
	h.shake = attack.shake
	h.stagger = attack.stagger
	h.launcher = attack.launcher
	h.heavy = attack.heavy
	h.direction = facing
	h.sfx = attack.sfx_hit
	h.source = get_parent()
	h.by_player = by_player
	var a := _shape.global_position
	h.position = Vector2(lerpf(a.x, hurt.center().x, 0.5), a.y)
	return h


func _draw() -> void:
	if Juice.debug_draw and _active:
		draw_rect(Rect2(_shape.position - _rect.size / 2.0, _rect.size), Color(1, 0.2, 0.2, 0.5))
