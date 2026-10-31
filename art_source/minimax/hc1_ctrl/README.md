# 第一刀候选 hc1_ctrl

2026-10-16，Codex，按 Devin 首轮复审整理。**候选待用户审阅；交 native 帧给 Devin 打包，尚未登记 clips.json 或导入游戏。**

先看 `hc1_ctrl_with_idle_closeup.gif`（前后加待机，便于循环观看），再看 `review/R010_cleanup_compare.png`。`hc1_ctrl_preview.gif` / `hc1_ctrl_preview_closeup.gif` 只包含招式建议时序；放大与裁切仅作用于预览。

## 帧与时序

- `native/` 有 10 张 256×256 RGBA：depth 代理的 R004、006、008、010、012、014、016，v02 的 C1、C2，以及原待机。
- 建议播放：**R004 1 → R006 1 → R008 2 → R010 1 → R012 3 → C1 2 → C2 1**，每格 1/12 秒，11 格约 0.917 秒，再交回待机。
- R014/R016 仅备用，不放进上述建议播放。它们源图脚底 y208，若选用，按 JSON 的 `[0,-1]` 偏移一次；PNG 没有烘焙偏移。其余实际播放帧的脚底天然在 y207，全部 x 偏移为 0。
- 命中在 R010→R012，零基 tick=5，约 0.417 秒；从 R010（tick=4）接受预输入；R012 第 2 格（hold_index=1，tick=6）至 C1 结束（tick=9，结束边界 tick=10）允许续刀。精确游戏判定/顿帧由 Devin 调节。
- 权威数据是 `hc1_ctrl_sequence.json`。`root_motion_px_estimate=null`，画布配准不冒充游戏位移。

## R010 的局部清理

使用上一轮 `depth_proxy/native_review/R010.png`，只改 alpha，不重新生图、不画剑、不拿 K5 替换。帧专用区域为原生画布 `[0,145,92,188)`，在其中保留身体的黄色/棕色调色板像素与相邻原描边，去掉剑光及其残留块。共清掉 **1263 个不透明像素**。

验证：保留像素的 RGB 未改；身体保护种子与保护描边的 RGBA 完全相同；区域之外完全相同；没有平移人物。鼻头浅色位于清理区域之外。原始生成帧与原 native_review 都保持不动。`review/` 留有清理前 native、移除蒙版、身体保护蒙版和放大前后对照，便于复审/撤回。

清完这一帧剑不可见，符合 Devin 此次处理约定；挥砍轨迹由 Devin 在游戏里补刀光。本候选本身没有制作刀光。其余生成帧逐像素复用，C1/C2/待机为源文件字节复制；全局 `prep_sprites.py` 未改。

## 验证和重现

`validation.json` 包含每张图的 SHA256、bbox、不透明面积、脚底、偏移与 R010 清理断言。10 张原生图仅使用批准的 17 色，alpha 仅 0/255；应用 JSON 偏移后脚底都是 y207。

JSON 采用精确 12fps；GIF 延迟只能用 10ms 单位，招式 GIF 共 910ms（与 11/12 秒约差 6.7ms），**以 JSON 为准**。前后待机停留只属于循环预览，不计入招式时序。

系统 Python 3.11（numpy / Pillow / cv2）从项目根运行：

```powershell
& 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe' tools/build_hc1_ctrl_candidate.py
```

本轮没有启动 ComfyUI、重新采样或修改游戏实现。待用户认可后采用 **native 直接交 Devin 打包**，不再把这批 native 反向登记成绿底视频走全局抠图。旧 v02 保底与首轮原片均保留。
