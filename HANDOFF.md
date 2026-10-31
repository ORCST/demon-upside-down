# 牛来游戏交接入口

最后同步：2026-10-31，Claude。开工先读 [沟通板](docs/协作/沟通板.md) 发给自己的待处理消息、[AGENTS.md](AGENTS.md)、本文和 [CLAUDE.md](CLAUDE.md)。每次完成后同步沟通板、[完成索引](docs/已完成/README.md) 和 HANDOFF。

## 城堡 C 已在游戏中；镜头上限已修（2026-10-31，Claude）

**当前游戏场景是城堡 C**（Devin 接入）：`assets/environment/castle_c/` 16 张图与 Codex 整理包一致，`castle_background.gd` 五层视差，`block.gd` 地面/木板贴图；旧 3D 城堡素材仍在仓库但未被引用。Camera `limit_top` 从 −200 改为 −84（= floor_y 300 − 墙高 384），二段跳到 Plat2/Plat5 上方不再露出墙顶；自动演示无错误，定向检查镜头顶边始终 ≥ −84。改墙高/地面高度时要同步此值。待用户实机试玩。见 [记录](docs/已完成/2026-10-31_城堡C场景接入与镜头上限修复.md)。下文 10-29 及更早“仍用 3D 城堡/场景未替换”均为历史。

## 当前仓库访问（2026-10-31 最新决定）

用户已明确授权将仓库改为**公开**。已完成修改，并验证未登录读取仓库 API 和 README 成功。地址：[https://github.com/ORCST/demon-upside-down](https://github.com/ORCST/demon-upside-down)，分支 `main`。Claude 可通过可用的网页/连接器读取；直接推送仍需写权限。详见 [公开与读取记录](docs/已完成/2026-10-31_仓库公开与Claude读取.md)。下方的“首次按私有同步”仅为历史过程，不再代表当前可见性。

## GitHub 同步（2026-10-31）

用户明确要求将截图中的 Devin 项目同步到 GitHub。已确认本机项目与 `block.gd` 对应，账户 ORCST，首次同步时目标为私有仓库（同日已按用户授权改为公开） [https://github.com/ORCST/demon-upside-down](https://github.com/ORCST/demon-upside-down)。首次完整源码快照已推送并核验远端 main；后续可直接使用 origin，验证结果见 [本次记录](docs/已完成/2026-10-31_GitHub项目同步.md)。现有游戏代码、美术源文件和工具纳入快照；未修改玩法或生产素材。

**源码现状补充：** 当前 `block.gd` 与 `castle_background.gd` 已引用 `assets/environment/castle_c/`；以下 10-29 的“仍用原有3D城堡 / 场景尚未替换”属于当时交接记录，不能覆盖当前源码事实。森林素材的后续制作状态本次未重新验收。

跨机器制作所需的 UAL 审看 `.blend`、`UAL1_Standard.glb`、KayKit glTF 源模块及许可证已显式纳入本次同步；其他录屏/试验导出仍忽略并保留在本机。后续开发分工不变。

## 最新分工与素材整理交付（2026-10-29）

**最新：用户已认可月夜森林图，明确“可以的拆分一下”；20项素材已交付。** 入口为 [forest_v01清单](art_source/environment/forest_v01/README.md)、[总览](art_source/environment/forest_v01/qa/asset_contact_sheet.png)、[完成记录](docs/已完成/2026-10-29_月夜森林素材拆分v01.md)。内置image_gen15次隔离/补全原图，再规范成20项原生PNG、32色、二值alpha及可延长桥/平台。原图 [森林概念](art_source/environment/forest_scene_concept_v01/forest_moonlight_ruins_v01.png) 保持不变；旧“待认可后拆分”已解决。

Devin可按manifest/README接手场景制作，核对视差、碰撞和实际滚动。桥分段48/96/48，石台/树枝16/64/16；视觉顶沿y/bbox已记录。月亮/废塔合在远景，水面静态；隔离补全件不是逐像素裁切，细节/比例有差异。2110个已有游戏/资产/主角3D/旧城堡包/原森林PNG等文件SHA256未变，本轮仅交素材，不搭关卡。前一城堡加道具整图仍仅作历史候选。

下述“只整理素材”是游戏制作分工；森林整图及拆分已获用户明确授权，素材已交。游戏制作和接入继续归Devin。

**此前的游戏制作分工仍有效：Codex整理素材，场景制作与接入归Devin。** 上轮城堡C整理包位于 [castle_c_v01](art_source/environment/castle_c_v01/README.md)，见 [记录](docs/已完成/2026-10-29_城堡C风格素材整理v01.md)。现有3D城堡继续保留，本轮森林素材交付本身没有改变游戏。

该目录已有16项原生PNG、12类源图14次内置生图记录（地面两项各修订一次）、manifest与qa。已有拼装预览只是素材检查，不是实机接入；2012个既有场景/脚本/资产/主角3D文件SHA256未变。收到最新指示后仅补清单和交接，不再生成或调整图像。Devin接手先读素材README的限制和切片规格。交接带整个castle_c_v01目录及已有处理脚本。

## 已确定的风格（Devin 记录，2026-10-29）

**用户选定 C 可爱卡通风格**（基准图 `castle_C_cartoon_v02.png`）。场景改走“GPT 生成拆分素材 → 统一像素化 → Devin 在 Godot 拼装”，需求见 [C 风格场景素材需求](docs/计划/2026-10-29_城堡C风格场景素材需求.md)，已在沟通板交给 Codex。现有 3D 场景 v01 暂时保留，等新素材到了再替换。

## 此前：城堡美术风格样张已交付

用户不满意现有城堡 v01 风格，2026-10-29 发来 Devin 的 [三风格提示词](docs/计划/2026-10-29_城堡场景风格概念图提示词.md) 截图。A/B/C样张已交付，**用户随后选定 C 暖紫 v02**；旧“等选风格/制作路线待定”已由最新决定替代。生产场景尚未替换。

- [A 经典恶魔城](art_source/environment/castle_style_studies_20261029/castle_A_classic_v01.png)：紫蓝哥特、细石纹，氛围浓。
- [B 现代精致像素](art_source/environment/castle_style_studies_20261029/castle_B_modern_v02.png)：青蓝月光/橙金火把，冷暖强，窗光较抢眼。
- [C 可爱卡通](art_source/environment/castle_style_studies_20261029/castle_C_cartoon_v02.png)：圆角大石砖、粗描边、大色块，更贴牛来的圆润外形。
- 内置 image_gen 共 5 次（A1/B2/C2），未选初稿留存。[完成记录](docs/已完成/2026-10-29_城堡场景三风格概念图v01.md)、[产物与提示词说明](art_source/environment/castle_style_studies_20261029/README.md)、verification_v01.json 已交付。
- 实际均 1672×941 RGB、接近16:9，**不是精确1280×720或已经统一640×360网格/24–32色的生产资产**。三图布局/比例略有差异，有平滑色阶/前景边缘；这是风格选择参考，不是实机录屏或成品分层背景。
- 此前 A 氛围/C 清晰度的组合只是建议；用户已明确选 C。后续制作由 Devin 依新分工执行，当前不新增角色/剧情/牛主题装饰。

## 游戏当前状态（他方记录，本轮未重跑）

- **（历史，已被城堡 C 替代）城堡内部 v01**，用户此前选定“城堡内部、先做场景”。KayKit 3D 模块 → 平涂渲染 →32色像素，后墙/石柱视差、火把光晕、石砖地面和木板平台。工具 `tools/scene3d_render.py` / `scene3d_pixelize.py`，素材 `assets/environment/castle/`。见 [10-27 城堡记录](docs/已完成/2026-10-27_城堡内部场景v01.md)。其“镜头升高露天空”已于 10-31 修复，详见原记录。
- **主角动画已全部统一 3D**，当前资源 `assets/sprites/niulai3d/niulai3d.tres`，由 `tools/niulai3d_pack.py` 打包。地面 J J J 为 hc1/hc2/hc3；移动 idle/run/jump/fall/land/dash/hurt/death 已换3D，10-27 其他攻击也用3D帧，并修上挑起手倒地。见 [10-18 三刀接入](docs/已完成/2026-10-18_HeavyCombo三刀接入游戏v01.md)、[10-20 移动接入](docs/已完成/2026-10-20_移动动作3D渲染接入v01.md)、[10-27 复查](docs/已完成/2026-10-27_接手复查与攻击姿势统一.md)。翻滚有渲染但未接入，未决定增加。
- **高刷新率移动发糊已由 Devin 修复，等用户实测**：物理插值、相机按物理帧跟随，见 [记录](docs/已完成/2026-10-27_高刷新率移动发糊修复.md)。玩法手感仍等用户实机试。

## 当前分工与有效限制

- **用户已将主角 3D 绑骨/套动作/渲染改派 Devin**，撤回了给 Codex 的模型任务。旧“还没有模型、Codex 等模型后绑骨”已过时，不能继续执行。
- 本轮城堡任务 Codex 只整理已有素材、规格和交接，场景制作接入归 Devin。主角3D改派同样有效：未经新任务不改 `tools/niulai3d_*.py`、`art_source/3d/model/`、`art_source/3d/render/`，不向旧 `assets/sprites/niulai/niulai.tres` 添加主角动画，不删除旧资源。
- Devin / Claude 负责现有 3D 管线和游戏呈现：`scripts/`、`scenes/`、招式/碰撞/刀光/顿帧。当前生产场景/脚本/精灵未在本轮修改。
- 所有代理通信通过沟通板；用户定美术风格、剧情、角色和设计取舍。例行文档同步无需重复确认。

## 模型、动作与历史资料

- 用户混元模型已交付，见 [检查记录](docs/已完成/2026-10-18_混元模型检查.md)。Devin 已绑骨文件 `art_source/3d/model/niulai_rig_v01.blend`，UAL2 `Sword_Heavy_Combo` 105 帧，防转身、方截面剑、内部线条、17色像素化，见 [3D 渲染记录](docs/已完成/2026-10-18_3D牛来绑骨与第一刀渲染v01.md)。这些是已有交付，本轮未复验。
- 动作来源：`outputs/motion_reference_20261015/ual2_review.blend`，Git 忽略，跨机器另带。用户主动作选 Heavy Combo，其他动作可给小怪。
- 牛来美术基准：`art_source/reference/poses/niulai_hd_idle.png`、`niulai_idle_tail_native.png` / x4。无角圆头、奶油鼻头、粗眉、粉耳、圆肚、棕短裤腰带蹄子、短尾深色尖。此前 [建模参考图](docs/已完成/2026-10-18_牛来3D建模参考图v01.md) 已被用户用于实际模型。
- v02 手绘关键帧仍留作历史/保底：`art_source/reference/poses/heavy_combo_v02/`。K4 已接受；K5 接入仅一次 `offset_px=[15,0]`，PNG未平移，不是游戏根位移。详见 [v02 记录](docs/已完成/2026-10-15_HeavyCombo第一刀关键帧v02修订.md)。
- MiniMax 暂停、Seedance 不用。旧 hc1_ctrl 偏弱，R008 脸糊、R010 清理缺手/剑，不入库；第二刀锚点提案暂停。旧文件保留，禁止按历史“下一步”自动恢复采样。升级和指定2.30GB补丁早已批准并完成，见 [10-16 记录](docs/已完成/2026-10-16_ComfyUI升级与控制视频首轮.md)。本轮没启动 ComfyUI 或下载模型。

## 环境与转交

项目 `D:/GoDOTProject/demon_unside_down`；Godot4.6.2、GDScript、640×360、整数缩放。角色约64px，精灵画布256²、身体中心x≈112、脚底最后像素y207（边界208）。Blender5.2.0 路径 `D:/Program Files/Blender Foundation/Blender 5.2/blender.exe`；系统Python3.11路径 `C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe`（Pillow/numpy/cv2/PyAV）。

本轮转交带整个 `art_source/environment/forest_v01/`，以及 `tools/prepare_forest_assets.py` 和其依赖 `tools/build_castle_c_assets.py`；获认可整图在 `forest_scene_concept_v01/`。旧城堡C包和风格样张另行留存，内置生图缓存已有项目内副本。旧游戏布局截图与KayKit源模型在Git忽略的outputs中，仅重现旧场景时另带；旧H3备份按需带。

上述“仅图像/文档、未提交推送”描述的是 10-29 的素材任务。2026-10-31 用户另行明确授权 GitHub 同步，现有未提交改动由本次任务统一保存；提交、运行验证与远端状态见顶部同步记录。
