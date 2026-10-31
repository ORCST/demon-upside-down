# Heavy Combo 第一刀：关键帧候选 v01

状态：已完成生成、像素规格校正和预览，**待用户审阅；尚未入游戏**。

## 先看

- `hc1_preview.gif`：标准画布，12fps 时序，最近邻 3 倍、背景 RGB(36,28,52)，循环一次 1.5 秒。
- `hc1_preview_closeup.gif`：同一时序与内容，统一裁切窗口放大，便于观看；没有逐帧自动跟随。
- `hc1_compare.png`：上排白模、下排牛来；C1/C2 为新设计的收招，没有白模原片。
- `hc1_detail.png`：牛来姿势排列，便于检查轮廓。
- `hc1_sequence.json`：Devin 使用的姿势顺序、停留时长、参考命中点和取消起点。数值为首轮预览方案，不是游戏内验收的参数。
- `hc1_validation.json`：尺寸、调色板、透明度、锚点、体型估计及旧文件保全结果。

本目录包括 K0 以及 8 张新姿势的 256×256 RGBA PNG。正式命名也已放在上级 poses：`niulai_hc1_k1_native.png`…`niulai_hc1_k6_native.png`、`niulai_hc1_c1_native.png`、`niulai_hc1_c2_native.png`，以及对应 `_x4.png` 和提示词。K0 沿用 `niulai_idle_tail_native.png`。

## 生成记录

使用 Codex 内置 image_gen。双参考输入可用，K1–K6 的首轮以牛来定稿＋对应白模截图为参考；C1/C2 以定稿＋K6 为参考。K5 第二轮使用首版、白模、定稿三张参考，修正后蹄离地。

共生成 9 次：K1/K2/K3/K4/K6/C1/C2 各 1 次，K5 共 2 次、采用第 2 次。首版 K5 的后蹄贴地已弃用，原图保留。完整记录在 `../_codex/hc1_attempts/generation_manifest.json`；所有原始生图、每次完整提示词也在该目录。原图实测 1254×1254，保留原样，再派生 256×256 原生图；不能将模型返回尺寸误记为 1024。

像素输出复用项目调色板与去噪/描边函数，再用带 `--poses` 筛选的新入口校正本批体型。后处理只做缩放、调色板、透明度、锚点与图表打包，不用代码重画角色或武器。

## 需要审阅的地方

- K4 是剑转入身体后方的遮挡/透视缩短，二维轮廓会显得像短剑；需要结合白模判断可读性，不能据这一帧推断物理剑长。
- K5 已修正后蹄抬起，剑接近侧刃，因此比其他姿势薄。像素体型校正通过，但头部和胸腹轮廓仍有逐张生成的细微差异。
- K3 以 R006 实际截图的剑向后上方为准，没有照抄计划里“指向后下方”的文字。K1 原片也主要是单手持剑，按截图安排握持。
- C1、C2 是本轮设计的两张收招，尚未在游戏中验证手感。K0 起止仍是原定稿。
- 当前 1.5 秒是用户计划指定的预览停留；是否压缩前摇、调整命中停顿和前冲，由用户审阅及 Devin 实机调节。

源视频是关闭根运动版本，不能可靠恢复原始前冲距离。JSON 将位移留空并注明待调，没有编造根位移数据。

## 复现后处理

用系统 Python 311，项目根目录运行：

```powershell
& 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe' tools/prepare_hc1_keyframes.py prepare
& 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe' tools/fix_pose_scale.py --poses hc1_k1 hc1_k2 hc1_k3 hc1_k4 hc1_k5 hc1_k6 hc1_c1 hc1_c2
& 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe' tools/prepare_hc1_keyframes.py package
```

`prepare` 保留 raw 文件，按 manifest 选择图像导出派生 native 输入；`fix_pose_scale` 仅处理选定 hc1 文件；`package` 整理位置和预览。该命令会重新生成本批 hc1 的派生输出，请保留任何人工修订的另名版本。

不需要 ComfyUI、模型下载或升级。未修改 `assets/`、`scripts/`、`scenes/`、`clips.json`。
