extends Node
## 启动时注册全部输入动作（键盘 + 手柄），并处理全局快捷键。
## 键位：A/D 移动  W/S 上下  K/空格 跳  J 轻攻击  U/I 重击  L/Shift 冲刺
## 手柄：左摇杆/十字键 移动  A 跳  X 轻攻击  Y 重击  RB/B 冲刺

const DEADZONE := 0.3


func _enter_tree() -> void:
	_add(&"move_left", [KEY_A, KEY_LEFT], [JOY_BUTTON_DPAD_LEFT], [[JOY_AXIS_LEFT_X, -1.0]])
	_add(&"move_right", [KEY_D, KEY_RIGHT], [JOY_BUTTON_DPAD_RIGHT], [[JOY_AXIS_LEFT_X, 1.0]])
	_add(&"move_up", [KEY_W, KEY_UP], [JOY_BUTTON_DPAD_UP], [[JOY_AXIS_LEFT_Y, -1.0]])
	_add(&"move_down", [KEY_S, KEY_DOWN], [JOY_BUTTON_DPAD_DOWN], [[JOY_AXIS_LEFT_Y, 1.0]])
	_add(&"jump", [KEY_K, KEY_SPACE], [JOY_BUTTON_A])
	_add(&"attack", [KEY_J], [JOY_BUTTON_X])
	_add(&"heavy", [KEY_U, KEY_I], [JOY_BUTTON_Y])
	_add(&"dash", [KEY_L, KEY_SHIFT], [JOY_BUTTON_RIGHT_SHOULDER, JOY_BUTTON_B])
	_add(&"debug_hitboxes", [KEY_F1])
	_add(&"toggle_fullscreen", [KEY_F11])
	_add(&"restart", [KEY_R])


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"toggle_fullscreen"):
		var w := get_window()
		w.mode = Window.MODE_WINDOWED if w.mode == Window.MODE_FULLSCREEN else Window.MODE_FULLSCREEN
	elif event.is_action_pressed(&"debug_hitboxes"):
		Juice.debug_draw = not Juice.debug_draw
	elif event.is_action_pressed(&"restart"):
		get_tree().reload_current_scene()


func _add(action: StringName, keys: Array = [], buttons: Array = [], axes: Array = []) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action, DEADZONE)
	for k in keys:
		var e := InputEventKey.new()
		e.physical_keycode = k
		InputMap.action_add_event(action, e)
	for b in buttons:
		var e := InputEventJoypadButton.new()
		e.button_index = b
		InputMap.action_add_event(action, e)
	for a in axes:
		var e := InputEventJoypadMotion.new()
		e.axis = a[0]
		e.axis_value = a[1]
		InputMap.action_add_event(action, e)
