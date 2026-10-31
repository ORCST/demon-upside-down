# 2026-10-18：Heavy Combo 三刀接入游戏 v01（Devin）

用户认可 3D 渲染效果（“可以的”）后，把主角从几何木偶换成牛来精灵，地面 J J J 换成 Heavy Combo 三刀。

## 改动

| 文件 | 内容 |
| --- | --- |
| `tools/niulai3d_pack.py`（新） | 打包 `assets/sprites/niulai3d/`：hc1/hc2/hc3（3D 渲染，12fps 偶数帧）、手绘 idle/run（沿用 `assets/sprites/niulai/`）、单张姿势 jump/fall/land/dash/hurt 和 atk_power/atk_uppercut/atk_air/atk_spike（取自 `art_source/reference/poses/`）。每帧都还原到 256 画布，锚点 (112, 208) |
| `scripts/visual/niulai_sprite.gd`（新） | 主角精灵显示。循环动画自己播放，攻击帧由玩家脚本按 `anim_timing` 指定，顿帧时自然定格；保留闪白、蓄力染色、挤压拉伸、冲刺残影 |
| `scripts/fx/slash_trail.gd`（新） | 刀光月牙，按招式的 `trail`（起止角度、半径）画，重击更粗 |
| `scripts/combat/attack_data.gd` | 新增 `anim`、`anim_timing`、`trail`、`trail_center`；删掉不再使用的 `Limb` |
| `scripts/player/player_attacks.gd` | jab1/jab2/kick3 换成 hc1/hc2/hc3；其他招式改成大剑判定框并配单张姿势；加了 `anim_timing` 总和校验 |
| `scripts/player/player.gd` | J 起手改为 hc1；hc1/hc2 接 U 出重击；出招时生成刀光，地面重击扬尘；`_update_rig` 改成选精灵动画；新增落地姿势计时 |
| `scenes/player.tscn` | Rig 节点改用 `niulai_sprite.gd` |
| `scripts/ui/hud.gd`、`scripts/debug/autopilot.gd` | 操作提示和演示脚本改成大剑说法 |
| `CLAUDE.md` | 目录表、3D 管线说明 |

## 三刀数据（60fps 物理帧；每张精灵帧的停留帧数见 `anim_timing`）

| 招式 | 画面（源帧） | 起手 / 判定 / 收招 | 伤害 | 备注 |
| --- | --- | --- | --- | --- |
| hc1 下撩 | R002–R016 | 19 / 6 / 15（命中约 0.33 秒） | 10 | 前冲 210，判定框 (40,-20) 62×30 |
| hc2 过肩斜劈 | R018–R030 | 14 / 6 / 16 | 12 | 前冲 170 |
| hc3 后仰砸地 | R030、R052–R066，加压地和起身 | 27 / 8 / 43 | 24 | 重击：蓄力发光、扬尘、顿帧 0.16 秒、震屏 0.6 |

取消窗口沿用原系统：判定结束后 `cancel_after` 帧起可以接下一刀，收招期间可以冲刺取消。

## 验证

- `--import` 没有脚本错误。
- 自动演示 `--autopilot=demo` 完整跑完：J J J 三刀全中（HUD 显示“3 HITS 46 DMG” = 10+12+24），重击、空中连段、打小恶魔、受击都正常，没有脚本错误。退出时有 1 条“resources still in use”提示，没有影响运行。
- 录屏帧在 `outputs/game_test_devin/movie/`；预览：`outputs/game_test_devin/combo_ingame.gif`、`full_frames.png`、`combo_sheet.png`（被 git 忽略）。
- 没有真人手柄或键盘实测，手感数值还要用户试了再调。

## 已知问题 / 下一步

- 画风混搭：idle/run 是手绘（更胖），攻击是 3D（偏瘦）；跳、冲刺、受击和空中招式还是单张姿势。可以从 UAL2 或其他动作库找待机、跑步、跳跃动作，用同一套 3D 管线渲染来统一。
- hc1/hc2 停手时直接回到待机，没有独立收招（源动作里没有）。
- hc3 收招 43 帧比较长，要看实际手感。
- 刀光和判定框的数值都是目测设定，需要实机调。
