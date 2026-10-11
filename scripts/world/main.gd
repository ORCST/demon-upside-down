extends Node2D
## 手感测试场。带 --autopilot 参数启动时自动演示。


func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--autopilot"):
			var pilot := preload("res://scripts/debug/autopilot.gd").new()
			add_child(pilot)
			break
