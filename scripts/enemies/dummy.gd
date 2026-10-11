extends Enemy
## 训练沙袋：打不死，2 秒没挨打就回满血。挨打会晃。

var _since_hit := 0.0
var _wobble := 0.0
var _wobble_v := 0.0


func _act(delta: float) -> void:
	super(delta)
	_since_hit += delta
	if _since_hit > 2.0:
		health = max_health


func _on_damaged(hit: HitData) -> void:
	_since_hit = 0.0
	_wobble_v -= 9.0 if hit.heavy else 5.0


func _pose(delta: float) -> void:
	super(delta)
	# 弹簧晃动，覆盖基类的倾斜
	_wobble_v += (-_wobble * 140.0 - _wobble_v * 7.0) * delta
	_wobble += _wobble_v * delta
	rig.lean = _wobble + (-0.6 if state == State.LAUNCHED else 0.0)
