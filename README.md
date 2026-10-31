# Demon Upside Down · 牛来

使用 **Godot 4.6.2 标准版 / GDScript** 制作的像素风横版动作游戏原型，内部画面为 640×360。

当前源码包含牛来主角的 3D 渲染像素动画、Heavy Combo 三连击、其他攻击和移动动作，以及城堡 C 风格背景、地面和平台。此仓库保存本机现有开发成果和素材，不代表游戏已完成。

## 运行

1. 克隆本仓库，使用 Godot 4.6.2 标准版打开根目录 `project.godot`。
2. 等待首次资源导入完成，按 F6 运行当前场景，或按 F5 运行项目。

命令行也可运行（将 `godot` 换成实际可执行文件路径）：

```powershell
godot --editor --path .
godot --path .
```

键盘操作：A/D 或方向键移动，K/空格跳跃，J 轻攻击，U/I 重击，L/Shift 冲刺，W/上＋攻击挑空，R 重开，F1 碰撞调试，F11 全屏。支持手柄。

## 项目内容

| 路径 | 内容 |
| --- | --- |
| `scripts/`、`scenes/`、`shaders/` | 游戏逻辑、场景和着色器 |
| `assets/`、`audio/` | 游戏运行所需的贴图、动画和声音 |
| `art_source/` | 美术源文件、模型、生成记录和历史候选；以 `.gdignore` 隔离自动导入 |
| `tools/` | 美术处理、渲染和视频工具 |
| `docs/`、`HANDOFF.md`、`CLAUDE.md` | 完成记录、协作交接和技术说明 |

为便于在其他机器继续制作，额外保存了原来位于 `outputs/` 的必要源输入：UAL 动作审看 `.blend`、工具使用的 `UAL1_Standard.glb`、KayKit 地牢 glTF 模块及相应授权说明。它们通过 Git 显式跟踪；其他 `outputs/` 录屏、试验导出、Godot 导入缓存和 Python 缓存均不上传。直接运行游戏不需要 Blender、ComfyUI 或重新生成美术。

离线美术管线的环境依赖和历史试验见 `CLAUDE.md`。首次接手先看 [HANDOFF.md](HANDOFF.md)、[协作规则](AGENTS.md) 和 [已完成目录](docs/已完成/README.md)。最新同步范围及验证结果见 [2026-10-31 记录](docs/已完成/2026-10-31_GitHub项目同步.md)。
