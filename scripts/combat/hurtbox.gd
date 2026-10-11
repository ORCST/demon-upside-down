class_name Hurtbox
extends Area2D
## 受击判定框。被 Hitbox 打中时发出 hurt 信号，由角色自己决定怎么挨打。

signal hurt(hit: HitData)

var invincible := false


func _ready() -> void:
	monitoring = false


func receive(hit: HitData) -> bool:
	if invincible:
		return false
	hurt.emit(hit)
	return true


func center() -> Vector2:
	for c in get_children():
		if c is CollisionShape2D:
			return c.global_position
	return global_position


func _physics_process(_delta: float) -> void:
	queue_redraw()


func _draw() -> void:
	if not Juice.debug_draw:
		return
	var col := Color(0.3, 1, 0.4, 0.35) if not invincible else Color(0.4, 0.6, 1, 0.35)
	for c in get_children():
		if c is CollisionShape2D and c.shape is RectangleShape2D:
			var size: Vector2 = c.shape.size
			draw_rect(Rect2(c.position - size / 2.0, size), col)
