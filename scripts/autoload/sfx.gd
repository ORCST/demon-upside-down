extends Node
## 音效播放池（自动加载为 Sfx）。音频不受 time_scale 影响，顿帧时打击声照样响。
## 现在的音效由 tools/gen_sfx.py 合成，是占位用的，之后直接替换同名 wav 即可。

const NAMES := [
	"whoosh_light", "whoosh_heavy", "hit_light", "hit_heavy", "ko",
	"jump", "land", "dash", "hurt", "bounce", "warn",
]
const VOICES := 16

var _streams := {}
var _players: Array[AudioStreamPlayer] = []
var _next := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for n in NAMES:
		var path := "res://audio/sfx/%s.wav" % n
		if ResourceLoader.exists(path):
			_streams[n] = load(path)
	for i in VOICES:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_players.append(p)


func play(sound: String, volume_db := 0.0, pitch_jitter := 0.08) -> void:
	var stream: AudioStream = _streams.get(sound)
	if stream == null:
		return
	var p := _players[_next]
	_next = (_next + 1) % _players.size()
	p.stream = stream
	p.volume_db = volume_db
	p.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
	p.play()
