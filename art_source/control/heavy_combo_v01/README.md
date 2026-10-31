# 第一刀控制素材 v01

2026-10-15，Codex。**技术检查通过，首帧握剑对齐待 Devin 复审；没有运行 AI 视频生成。**

先看 `control_compare.mp4`（上：原比例，下：比例代理；三列：灰模、深度、Canny 轮廓），再看 `frame0_alignment.png` 和 `anchor_alignment.png`。评审视频用了统一裁切放大，**不能当模型输入**；各变体目录中的 PNG / MP4 才是固定 768×768 控制素材。

## 内容

| 路径 | 内容 |
| --- | --- |
| `original/` | 原成人比例，保留源关节旋转与时序，做统一接地修正 |
| `proxy/` | 缩短腿、躯干和手臂，放大头部的比例代理；不是牛来精确模型 |
| `<变体>/beauty/`、`beauty.mp4` | 灰模＋蓝色参考大剑，仅便于审查 |
| `<变体>/depth/`、`depth.mp4` | 8 位深度，近白远暗，黑底 |
| `<变体>/depth16/` | 16 位无损深度母版 |
| `<变体>/lineart/`、`lineart.mp4` | 从深度与前景边界提取的白线黑底 Canny，非手绘线稿 |
| `<变体>/mask/`、`sword_mask/` | 可见前景与可见武器二值蒙版；遵循真实遮挡 |
| `<变体>/geometry/`、`cache/` | Blender 求值的投影三角形，以及光栅化原始深度缓存，支持重建 |
| `inputs/` | 绿底待机首帧，以及 K2 / K4 v02 / K6 中间锚点 |
| `anchor_manifest.json` | R000 待机、R005 K2、R008 K4、R012 K6 的对应关系、源文件和哈希 |
| `render_manifest.json` | 投影、尺寸、比例参数、接地修正、统一深度区间和逐帧统计 |
| `verification.json` | 288 张控制 PNG、4 张输入、7 个 MP4 的验证证据和来源哈希 |

## 尺寸与时序

- 单人、正交纯侧视、面朝右，768×768，24fps。每版 24 帧，严格对应源 R000–R023，视频 1 秒。
- R000–R017 是本次主体，R018–R023 是续动作余量，已经进入下一刀准备，**不是独立回待机收招**。
- R000 身体高度 192px、骨盆中心 x336；身体最低点边界 y624，最后占用像素行为 y623。两版使用各自固定比例，后续帧不自动缩放、不跟随镜头、不水平重居中。
- 原比例也存在源动作脚底穿地，最大约 13px。两版均统一平移整个人物＋剑进行接地，关节角度、水平动作和采样时间不变。每帧修正量保存在 manifest，不是游戏根位移数据；此方法不能直接套用跳跃。
- 参考剑重建为同尺寸刚体，绑定原有持剑手方向；刀身长 198px、宽 30px、厚 6px，护手宽 42px、柄长 28px。尺寸在两版相同，投影长度会随挥剑朝向变化。R008 刀身被身体遮挡是源动作特征，未强行画穿身体。
- 深度由 Blender 求值后的真实三角形几何经 CPU 正交 z-buffer 光栅化得到。两版、全部帧共用一个深度区间，没有逐帧归一化，因此不会因每帧自动拉伸产生明暗跳变。MP4 有损，优先用无损 PNG 母版。

## 尚需解决

1. `frame0_alignment.png` 显示脚底和站立高度已对齐，但白模持剑点比牛来待机偏后，剑角也不同。原比例参考握点约 `[325,525]`，代理约 `[329,550]`（768 画布）。因此本批不能标为“首帧完全匹配”；Devin 应先判断是否要做起始姿势过渡，再采样。
2. 代理仍是人形网格，不能据此宣称已经解决牛来体型保持问题；这要由实际生成试验验证。
3. 本机现有 `nodes_minimax_h3.py` 把视频长度向上对齐到 `17k+5` 帧，24 会成为 39。**本批没有补帧或改速**；后续接 ControlNet 时须明确选择截到 22 帧或显式补齐 39 帧并保留映射，不可假定能直接提交 24 帧。较短输出的动作质量也未验证。
4. 升级后确认实际 Fun ControlNet / 中间锚点节点和输入约定。本批没有构造或提交 Comfy 工作流，也没有新增 `job.json`；没有生成“白模与牛来生成结果”并排视频。

## 重现

从项目根目录依次执行（PowerShell）：

```powershell
& 'D:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python tools/export_control_heavy_combo.py
& 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe' tools/render_control_heavy_combo.py
& 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe' tools/prepare_control_heavy_inputs.py
```

Blender 5.2.0；系统 Python 3.11，依赖 numpy、Pillow、opencv-python、PyAV；视频编码 libx264。脚本只重建本目录，不改源 blend、v02 姿势、游戏代码或 assets。

来源：`outputs/motion_reference_20261015/ual2_review.blend`，动作 `Sword_Heavy_Combo`。`outputs/` 被 Git 忽略，跨机器重现须额外携带源 blend；仅审查和后续接入可直接携带本目录与参考姿势。当前本目录约 10.6MiB，本地存在不等于已经提交或传到远程。
