# 39 帧原速控制素材

2026-10-15，Codex，按 Devin 对 v01 的复审意见扩展。源动作 `Sword_Heavy_Combo`，**R000–R038 连续原帧，24fps，1.625 秒**；没有插值、复制补帧或改速，已满足 H3 的 17k+5 网格。原来的 `heavy_combo_v01/`（24 帧）全目录保留并通过逐文件哈希验证未改。

两版 `original/`、`proxy/` 均为单人正交侧视 768×768；保持 v01 的体型参数、固定相机、刚体参考剑和整体接地方式。R000 身体高 192px、骨盆 x336，全部帧脚底最后占用行 y623。全部 78 帧共享一个深度区间；由于新增帧参与区间计算，不能要求前 24 帧的归一化深度值与 v01 字节相同。

- 每版 `depth/`、`lineart/`（Canny）、`beauty/` 及对应 MP4 是模型控制/检查素材；`depth16/`、`mask/`、`sword_mask/` 和几何缓存同 v01 格式。
- `control_compare.mp4` 上原比例、下代理，列为灰模/depth/Canny，用统一裁切放大供评审，不能当模型输入。
- `inputs/` 与 `anchor_manifest.json`：R000 牛来待机绿底首帧，**K4@R008、K6@R012**。第一轮排除 K2；新原生节点 `MiniMaxH3AddGuide.frame_idx` 接受像素帧号，当前正索引可直接填 8、12。
- `frame0_alignment.png` 的握点/剑角差异由 Devin 接受，第一轮不加起始过渡。生成后仍须检查 R000–R004 融化、持剑手缩进腹部或手臂被拉长。
- R013 后没有额外牛来锚点；R024–R038 继续源动作，用于测试 ControlNet 维持动作和外观的能力。本段没有独立停手收招。
- `verification.json`：468 张控制 PNG、3 张绿底输入、7 个 MP4 检查通过，视频全部 39 帧/24fps/1.625 秒，投影几何没有越界。技术检查不代表生成质量已通过。

重现（项目根目录 PowerShell）：

```powershell
& 'D:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python tools/export_control_heavy_combo.py -- --output art_source/control/heavy_combo_v02_39f --frames 39
& 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe' tools/render_control_heavy_combo.py --output art_source/control/heavy_combo_v02_39f
& 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe' tools/prepare_control_heavy_inputs.py --output art_source/control/heavy_combo_v02_39f --first-trial
```

依赖 Blender 5.2.0、系统 Python 3.11（numpy/Pillow/cv2/PyAV）。源场景 `outputs/motion_reference_20261015/ual2_review.blend` 位于 Git 忽略目录，跨机器重现需要另带；本目录约 17MiB，可直接转交审查。没有改游戏 assets 或代码。
