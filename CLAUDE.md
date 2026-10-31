# 牛来 · 恶魔城（demon_unside_down）

> 接手先读 [HANDOFF.md](HANDOFF.md) 和 [AGENTS.md](AGENTS.md)。用户要求每次完成工作后同步 [项目已完成目录](docs/已完成/README.md) 与 HANDOFF。最新决定：牛来主攻参考为 Universal 的 `Sword_Heavy_Combo`，其他动作留给小怪。**2026-10-18 起美术走“3D 模型渲染成像素”**（见下方“3D 管线”），Heavy Combo 三刀已接入游戏（J J J）。下面的 MiniMax 动画管线是历史实验。

送朋友的生日礼物：像素风恶魔城（Metroidvania）。主角是梗图电影《牛来》里的小牛，拿大剑去拯救牛妈妈。
**剧情、角色、美术风格由主人决定**：先列计划和问题（每题给推荐项），等回复再动手；纯技术选择可以自己定，事后汇报。

## 技术约定

2026-10-29 场景任务最新分工：用户选 C 暖紫 v02，Codex **只整理素材、不直接制作**；整理包位于 `art_source/environment/castle_c_v01/`，后续场景制作与接入归 Devin，当前仍用原有3D城堡。细节见 HANDOFF 与沟通板。

同日最新：用户已认可 `art_source/environment/forest_scene_concept_v01/` 月夜森林整图并明确“可以的拆分一下”。`art_source/environment/forest_v01/` 已交20项原生PNG、32色、切片/平铺检查与清单，后续制作/接入归Devin。旧“待认可后拆分”已解决，游戏及既有城堡包未改。

- Godot 4.6.2 标准版 + GDScript：`D:\GoDOTProject\Godot_v4.6.2-stable_win64\`
- 内部分辨率 640×360，整数放大；角色站立约 64 像素高，精灵 1:1 显示
- 手写 `.tscn` 里导出的节点引用要写 `node_paths=PackedStringArray("属性名")`，否则是 null
- 原始美术放 `art_source/`（有 `.gdignore`，Godot 不导入）；进游戏的素材放 `assets/`，由 `tools/` 下的脚本生成

## 目录

| 路径 | 内容 |
|---|---|
| `scripts/autoload/` | `Juice`（顿帧/震屏/慢动作/特效）、`Sfx`（音效池）、`GameInput`（键位） |
| `scripts/combat/` | `AttackData` 招式数据、`Hitbox` / `Hurtbox`、`HitData` |
| `scripts/player/` | 主角控制器；`player_attacks.gd` 是招式表（hc1–hc3 = Heavy Combo 三刀，`anim_timing` 逐帧对应精灵） |
| `scripts/visual/niulai_sprite.gd` | 主角精灵显示（`assets/sprites/niulai3d/niulai3d.tres`）；攻击帧由玩家脚本按招式帧数指定 |
| `scripts/visual/puppet.gd` | 几何占位角色，现在只给敌人用 |
| `scripts/fx/slash_trail.gd` | 刀光月牙（招式里的 `trail` 参数控制角度和半径） |
| `art_source/3d/` | 混元牛来模型、绑骨文件 `model/niulai_rig_v01.blend`、渲染 `render/heavy_combo_v01/` |
| `assets/environment/castle/` | 城堡场景贴图（后墙、石柱、地面块、木板），由 `tools/scene3d_render.py` → `scene3d_pixelize.py` 从 KayKit 3D 模块渲染；`scripts/world/castle_background.gd` 搭视差层，`block.gd` 平铺地面贴图 |
| `assets/sprites/niulai3d/` | 主角当前用的精灵：hc1–hc3、移动动作和其他攻击均已统一 3D（10-27）；由 `tools/niulai3d_pack.py` 生成，Codex 本轮不改此管线 |
| `scripts/debug/autopilot.gd` | 自动演示脚本（录屏 / 回归测试用） |
| `scenes/debug/anim_preview.tscn` | 把 `niulai.tres` 的所有动画并排播放 |
| `docs/art/美术需求与提示词.md` | 给 Codex/GPT 的美术需求单和提示词 |
| `art_source/reference/` | 旧基准图 `niulai_idle_canvas256.png`（无尾巴，已不用） |
| `art_source/reference/poses/` | **现在的基准**：`niulai_idle_tail_native.png` 和 14 个关键姿势（标准画布 256×256，脚底 y=208，身体中心 x≈112，17 色）。Codex 原图在 `_codex/`，用 `tools/fix_pose_scale.py` 统一了身体大小（Codex 会按剑长缩放，身体差 ±20%） |
| `art_source/minimax/` | H3 的输入（`input/`）、生成的视频和帧、`clips.json` 动画清单、`preview/` |
| `assets/sprites/niulai/` | 生成的精灵表 + `niulai.tres`（SpriteFrames，每帧用 AtlasTexture margin 还原到 256 画布，锚点一致） |

## 3D 管线（当前）

1. `blender --background --python tools/niulai3d_build_rig.py`：混元模型 → UAL2 骨骼 → 烘焙 `Sword_Heavy_Combo`（含防转身、方截面剑）→ `art_source/3d/model/niulai_rig_v01.blend`。需要被 git 忽略的 `outputs/motion_reference_20261015/ual2_review.blend`。
2. `blender --background --python tools/niulai3d_render.py -- 起 止`：4 倍超采样卡通渲染＋深度图。
3. `py tools/niulai3d_pixelize.py`：17 色、描边、内部线条 → `native/Fnnn.png`。
4. 持剑架势：`blender --background --python tools/niulai3d_guard_idle.py` 生成 `guard_idle` 和 `jog/sprint/jump_*_carry`，每个再跑 `niulai3d_render.py -- <名字>` 和 `niulai3d_pixelize.py <名字>`（重跑第 1 步后要重跑这一步）。
5. `py tools/niulai3d_pack.py`：选帧打包成 `assets/sprites/niulai3d/`。改了剪辑帧号后，记得同步 `player_attacks.gd` 的 `anim_timing`。
6. 验证：`Godot_v4.6.2-stable_win64_console.exe --path . --write-movie outputs/x/f.png --fixed-fps 60 -- --autopilot=demo --shots=<目录>`，看日志里的伤害和截图。

## 动画管线（MiniMax，历史）

**MiniMax 已暂停。** 用户模型已交回，绑骨/渲染已改派 Devin，三刀和移动动作已接入；“等模型、Codex继续绑骨”是过时任务。下面MiniMax经验保留作历史。2026-10-29用户已选C场景风格，Codex仅整理现有 `art_source/environment/castle_c_v01/` 素材与说明，制作接入由Devin负责；游戏当前仍用原有3D城堡。详见HANDOFF和沟通板。

1. **ComfyUI 不用开窗口**，后台启动服务（端口 8189）：
   `D:/Comfy-Desktop/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/Scripts/python.exe main.py --port 8189 --models-directory D:/Comfy-Desktop/ComfyUI-Shared/models --output-directory D:/Comfy-Desktop/ComfyUI-Shared/output --disable-auto-launch`（在 `ComfyUI-Installs/ComfyUI/ComfyUI` 目录下运行）
2. `tools/comfy_minimax.py`：跑 MiniMax H3 首尾帧生视频。输入是标准画布放大 3 倍垫纯绿底（768×768）。3 秒约 2.5 分钟。
3. 在 `art_source/minimax/clips.json` 登记，然后 `py tools/prep_sprites.py [名字]`：抠绿 → 对齐 → 缩到原生像素 → 吸附 17 色 → 描边 → 精灵表 + `niulai.tres`。
4. 用 `anim_preview.tscn` 录屏检查（Movie Maker：`--write-movie x/f.png --fixed-fps 60`），再用 `tools/encode_movie.py` 转 MP4（要用 ComfyUI venv 的 Python，它有 PyAV）。

H3 的经验：
- 像素图直接当输入，像素风格保持得很好
- 会自己加剑光、火花，还会转身朝镜头。**提示词里不要点名"不要剑光/火花"**：越提越多，背景还会闪红（slash v2 的教训）。用正面描述 + 首尾关键姿势来约束
- `prep_sprites.py` 会自动删掉大块偏蓝的亮白剑光，并警告背景不是绿色的帧
- H3 总给牛来加尾巴 → 2026-10-10 决定：尾巴成为设定（美术文档 T0）。T0 交付后，基准图换成带尾巴的版本，`input/` 里的绿底首帧也要重做

## 工具用的 Python

- 普通脚本：`C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe`（有 numpy / PIL / cv2）
- 需要 PyAV 的（编码视频）：ComfyUI 的 `.venv/Scripts/python.exe`
