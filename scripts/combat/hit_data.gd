class_name HitData
extends RefCounted
## 一次命中的结果：Hitbox 生成，交给 Hurtbox 的主人处理，同时交给 Juice 出反馈。

var damage := 1
## 已按出招方向翻转过的击退速度
var knockback := Vector2.ZERO
var hitstop := 0.06
var shake := 0.15
var stagger := 0.3
var launcher := false
var heavy := false
var direction := 1
## 命中点（世界坐标），特效从这里出
var position := Vector2.ZERO
var sfx := "hit_light"
var source: Node
var by_player := false
