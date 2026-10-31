# Heavy Combo 视频控制首轮

完成于 2026-10-16，Codex。**本地生成管线已跑通，三组画面均未达到游戏素材入库标准。** 本次确实输入了白模控制视频，并使用牛来首帧、K4/K6 中间锚点。

> 后续复审更新：Devin 认为 depth 代理的 **R000–R016 第一刀可经局部清理整理为候选**；并非 39 帧整段通过。候选已另存到 [hc1_ctrl](../hc1_ctrl/README.md)，R010 只清剑光、收招接 v02 C1/C2，待用户审阅。下面保留的是整段首轮审查记录。

## 先看

- `trial_compare_half_speed.mp4`：四列依次为代理白模、成人比例 depth、比例代理 depth、比例代理 Canny；半速供审查。`trial_compare.mp4` 是原速 24fps。
- `trial_compare_keyframes.png`：R000、003、008、010、012、016、024、038 对照。
- 各组 `reference_vs_generated.mp4` / `reference_vs_generated_half_speed.mp4`：对应比例的白模与牛来左右并排。
- 各组 `raw_contact_sheet.png` 保留原始生成缺陷；`native_contact_sheet.png` / `native_preview.gif` 是像素化诊断，不能用清理结果冒充原片合格。

| 目录 | 完成情况 | 本次结论 | 执行时间 |
| --- | --- | --- | --- |
| `depth_original/` | 首次默认启动，采样初始化原生崩溃，0 帧 | 保留失败 job / workflow / 日志指针，无完整 history | 未完成 |
| `depth_original_attempt02/` | 兼容启动成功，39 帧 | 后半段身体被拉细、转身，R010/R014 灰色剑拖影；不入库 | 92.88 秒 |
| `depth_proxy/` | 成功，39 帧 | 三组里体型和朝向最好；R010/R024 仍有大片白色剑光，R028 手臂异常；不入库 | 72.78 秒 |
| `lineart_proxy/` | 成功，39 帧 | Canny 未消除剑光，R003–006 正面化，后半段脸部丢失/转身；不入库 | 70.89 秒 |

时间由各组 history 的执行开始/成功时间戳计算，不含升级和下载。每种条件只试同一颗种子，这些结论限于本轮，不能视为模型通用排名。

## 参数与实际连接

- 控制源：`art_source/control/heavy_combo_v02_39f/`，R000–R038，24fps，768×768，39 个连续原帧。未改速、未复制补帧；K2 不参与本轮。
- 现有 fl2va int8 convrot 主模型、Qwen3-VL nvfp4 文本编码器、fp16 视频 VAE、fl2v turbo 8step LoRA；没有下载 Ref2VA 主模型，也没有使用云端服务。
- 种子 `20261015`，8 步，`res_multistep` / `simple` / BasicGuider，ControlNet strength=1、start=0、end=1。
- `LoadVideo → GetVideoComponents.images → MiniMaxH3FunControlNetApply.control_video`，不是只用文字描述动作。
- 绿底待机作为 `MiniMaxH3ImageToVideo.first_frame`；原生 `MiniMaxH3AddGuide` 串联 K4 `frame_idx=8`、K6 `frame_idx=12`。输入是像素帧号；每组具体连接保存在 `workflow_api.json`。
- 动作参考视频导出为静音；H3 内部仍采样视频/音频联合 latent，但本次不做音频 VAE 解码。

## 文件与验证

每个成功目录均有 `job.json`、`prompt.txt`、`workflow_api.json`、`node_schemas.json`、`history.json`、`generated.mp4`、`frames/R000.png`–`R038.png`、`review.json`。`native_review/` 只是诊断图，没有登记到 `clips.json` 或写入游戏 assets。

`trial_results.json` 汇总种子对应的真实 prompt_id、耗时、源文件哈希和人工结论。技术上 3 段生成视频共 117 帧均可解码，9 个分组视频（原片/对照/半速）已验证；根目录 2 个综合对照另见交付验证文件。所有原片 39 帧、24fps、1.625 秒；半速版 12fps、3.25 秒，不能误当原速动作。

原生像素诊断不透明面积范围：成人 depth 1081–5314，代理 depth 1524–4083，代理 Canny 1435–2711。面积较稳不代表脸、剑或动作合格；例如 Canny 后半段面部细节已丢失。

## 环境与兼容处理

用户已批准的升级和补丁安装已完成：ComfyUI **0.35.0**（`40c4fcdf513a4523e39d54a9d391908af8df8171`），pip check 通过；补丁文件 2,296,635,360 字节，官方 LFS SHA256 为 `9c645c0a308c8af361efd43b409710f6f8fec0db297c29503e141a84991fed0c`，下载后完整匹配。

默认启动第一次在 `comfy/ldm/minimax/model.py:586` 原生 abort。添加官方已有启动参数 `--disable-comfy-compiler` 后，用相同输入/种子完成三组试验；DynamicVRAM 和 PyTorch attention 保留，没有修改 ComfyUI 源码。这与 [官方仓库故障报告 #16230](https://github.com/Comfy-Org/ComfyUI/issues/16230) 的规避方式一致，不能据此宣称已查明底层根因。

可复用启动脚本：`tools/start_h3_control_comfy.ps1`，隐藏启动，127.0.0.1:8189，独立项目输入/输出目录，含该兼容参数；已存在服务则不会重复启动。生成结束后服务已关闭；原数据库路径已从启动时自动生成的 `.bak` 恢复并做字节校验。审计见 `outputs/h3_control_setup_20261015/upgrade_manifest.json`、`patch_install.json`、`shutdown_report.json`。

## 后续与转交

先交 Devin 复审，保留 depth 代理作为下一轮对照；重点看快挥时剑形丢失、R003 起始姿态过渡与手/腹部关系，再决定是否尝试更合适的代理或锚点。此轮没有重抽种子，也没有扩展完整连招/补独立收招。

复现入口：系统 Python 3.11 运行 `tools/run_h3_control_heavy.py <original|proxy> [--control depth|lineart] [--attempt N]`；已有 job.json 的目录一律跳过，`--collect` 只收集已提交任务。需要重试时另开 attempt，不能删除 job 重提。审查与综合对照工具是 `tools/review_h3_control_heavy.py`、`tools/compare_h3_control_trials.py`。

这些文件仍是本地产物，未提交/推送。跨机器审查带本目录与控制素材目录即可；完整重跑还需要本机已有大模型。`outputs/` 被 Git 忽略，另带必要的日志/安装清单；运行目录中的 `comfy_user/` 不是交付必需项。没有改 `assets/`、`clips.json`、`scripts/` 或 `scenes/`。
