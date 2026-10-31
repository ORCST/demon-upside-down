# 3D 牛来 Heavy Combo 渲染 v01

2026-10-18，Devin。**候选，待用户看效果；没有入库，也没有接入游戏。**

## 先看

- `preview_cut1_12fps.gif`：第一刀 R000–R016 的偶数帧，12fps，放大 3 倍。
- `preview_all_24fps.gif`：已渲染的 R000–R038 全部帧，24fps，包含第二刀前半。
- `compare_vs_keyframes.png`：上排是 3D 渲染，下排是关键帧 v02（K0/K4/K5/K6）。

## 目录

| 路径 | 内容 |
| --- | --- |
| `native/Fnnn.png` | 256×256 原生像素帧（17 色、1px 描边、内部线条），脚底 y=207，站立身体中心 x≈112 |
| `color/`、`depth/` | 1024×1024 的 4 倍超采样渲染：卡通颜色＋16 位身体深度（用来画内部线条） |
| `native_stats.json` | 每帧包围盒、不透明像素数 |

## 重现

在项目根目录（PowerShell）：

```powershell
& 'D:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python tools/niulai3d_build_rig.py
& 'D:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python tools/niulai3d_render.py -- 0 38
& 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe' tools/niulai3d_pixelize.py
```

- 绑骨脚本需要 `outputs/motion_reference_20261015/ual2_review.blend`（被 git 忽略，跨机器要另外带上）。
- 绑骨结果：`art_source/3d/model/niulai_rig_v01.blend`，报告是同目录的 `niulai_rig_v01_report.json`。
