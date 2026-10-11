extends Node
## 自动演示：按脚本模拟按键，用来录制手感演示视频和截图。
## 用法：Godot --path . --write-movie out/frame.png --fixed-fps 60 -- --autopilot=demo [--shots=目录]
## 计时按"真实帧"算，不受顿帧影响，跟真人按键一样。

const SCRIPTS := {
	"demo": [
		["wait", 30], ["log", "start"],
		["approach", "Dummy", 30], ["wait", 6],
		# 三连：刺拳 刺拳 回旋踢
		["tap", "attack"], ["wait", 13], ["tap", "attack"], ["wait", 13], ["tap", "attack"],
		["wait", 12], ["shot", "kick3"], ["log", "kick3"], ["wait", 30],
		# 刺拳 刺拳 重拳
		["approach", "Dummy", 30],
		["tap", "attack"], ["wait", 13], ["tap", "attack"], ["wait", 13], ["tap", "heavy"],
		["wait", 16], ["shot", "power"], ["log", "power"], ["wait", 50],
		# 上勾拳挑空 → 跳起 → 空中踢两段 → 下劈砸地
		["approach", "Dummy", 24],
		["press", "move_up"], ["tap", "attack"], ["release", "move_up"], ["wait", 16],
		["hold", "jump", 12], ["tap", "attack"], ["wait", 12], ["tap", "attack"],
		["wait", 12], ["shot", "air"], ["tap", "heavy"], ["wait", 20], ["shot", "spike"], ["log", "air"], ["wait", 40],
		# 去打小恶魔
		["approach", "Grunt", 30],
		["tap", "attack"], ["wait", 13], ["tap", "attack"], ["wait", 13], ["tap", "attack"], ["wait", 40],
		["log", "grunt_combo1"],
		["approach", "Grunt", 30],
		["tap", "attack"], ["wait", 13], ["tap", "attack"], ["wait", 13], ["tap", "heavy"], ["wait", 14],
		["shot", "kill"], ["log", "grunt_kill"], ["wait", 80],
		# 第二只：先站着挨一拳，再冲刺躲开反打
		["approach", "Grunt2", 40], ["wait", 50], ["shot", "hurt"], ["log", "got_hit"], ["wait", 30],
		["approach", "Grunt2", 26],
		["press", "move_up"], ["tap", "attack"], ["release", "move_up"], ["wait", 16],
		["hold", "jump", 12], ["tap", "attack"], ["wait", 12], ["tap", "attack"], ["wait", 12],
		["tap", "heavy"], ["wait", 40], ["log", "juggle"],
		["approach", "Grunt2", 30],
		["tap", "attack"], ["wait", 13], ["tap", "attack"], ["wait", 13], ["tap", "heavy"], ["wait", 30],
		["approach", "Grunt2", 30], ["tap", "attack"], ["wait", 14], ["shot", "finish"], ["wait", 16],
		["log", "end"], ["wait", 90],
		["quit"],
	],
}

var _steps: Array = []
var _i := 0
var _wait := 0
var _held: StringName = &""
var _shots_dir := ""
var _approach := ""
var _approach_dist := 0.0
var _approach_frames := 0
var _approach_dir: StringName = &""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var script_name := "demo"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--autopilot="):
			script_name = arg.get_slice("=", 1)
		elif arg.begins_with("--shots="):
			_shots_dir = arg.get_slice("=", 1)
	_steps = SCRIPTS.get(script_name, [])


func _process(_delta: float) -> void:
	if _approach != "":
		_step_approach()
		return
	if _wait > 0:
		_wait -= 1
		if _wait == 0 and _held != &"":
			_send(_held, false)
			_held = &""
		return
	while _i < _steps.size() and _wait == 0 and _approach == "":
		_run(_steps[_i])
		_i += 1


func _run(step: Array) -> void:
	match step[0]:
		"wait":
			_wait = step[1]
		"hold":
			_held = StringName(step[1])
			_send(_held, true)
			_wait = step[2]
		"tap":
			_held = StringName(step[1])
			_send(_held, true)
			_wait = 2
		"press":
			_send(StringName(step[1]), true)
		"release":
			_send(StringName(step[1]), false)
		"shot":
			if _shots_dir != "":
				var img := get_viewport().get_texture().get_image()
				img.save_png(_shots_dir.path_join("%s.png" % step[1]))
		"approach":
			_approach = step[1]
			_approach_dist = step[2]
			_approach_frames = 0
		"log":
			_log(str(step[1]) if step.size() > 1 else "")
		"quit":
			get_tree().quit()


## 朝指定敌人走，直到距离 <= _approach_dist（最多 5 秒）
func _step_approach() -> void:
	var p := get_tree().get_first_node_in_group(&"player") as Node2D
	var target := get_tree().current_scene.find_child(_approach, true, false) as Node2D
	_approach_frames += 1
	var want: StringName = &""
	if p and target and _approach_frames < 300:
		var dx := target.global_position.x - p.global_position.x
		if absf(dx) > _approach_dist:
			want = &"move_right" if dx > 0.0 else &"move_left"
	if want != _approach_dir:
		if _approach_dir != &"":
			_send(_approach_dir, false)
		if want != &"":
			_send(want, true)
		_approach_dir = want
	if want == &"":
		_approach = ""
		# 碰到台阶就跳过去
	elif p is CharacterBody2D and (p as CharacterBody2D).is_on_wall() and (p as CharacterBody2D).is_on_floor():
		_send(&"jump", true)
		get_tree().create_timer(0.25, true, false, true).timeout.connect(_send.bind(&"jump", false))


func _log(tag: String) -> void:
	var p := get_tree().get_first_node_in_group(&"player") as Player
	var cam := get_viewport().get_camera_2d()
	var line := "[autopilot %s] frame=%d" % [tag, Engine.get_process_frames()]
	if p:
		line += " player=%s state=%d hp=%d floor=%s" % [p.global_position.round(), p.state, p.health, p.is_on_floor()]
	if cam:
		line += " cam=%s" % cam.get_screen_center_position().round()
	for e in get_tree().get_nodes_in_group(&"enemies"):
		line += " %s=%s/%d" % [e.name, (e as Node2D).global_position.round(), e.health]
	print(line)


func _send(action: StringName, pressed: bool) -> void:
	var e := InputEventAction.new()
	e.action = action
	e.pressed = pressed
	e.strength = 1.0 if pressed else 0.0
	Input.parse_input_event(e)
