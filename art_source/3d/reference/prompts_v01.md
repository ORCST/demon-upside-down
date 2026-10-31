# 牛来 3D 建模参考图 v01：生图提示词

工具：内置 `image_gen`（imagegen 技能默认路径）；纯白背景，不透明 PNG。用途为混元 3D 建模参考，不是游戏精灵。
输入：`art_source/reference/poses/niulai_hd_idle.png`、`niulai_idle_tail_x4.png`。第二张侧视还引用本轮正面图，以锁定比例与配色。

## 正面 / front_attempt01

Use case: stylized-concept.
Asset type: a single full-body orthographic FRONT modeling reference of the established Niulai calf character for image-to-3D reconstruction.
Input images: Image 1 is the approved smooth illustration and is the character identity reference. Image 2 is the approved native pixel-art look enlarged, and is the silhouette/color reference. Both depict the SAME character. Do not reproduce their sword or fighting pose.
Primary request: redraw this exact hornless golden-yellow calf in a neutral, symmetrical A pose, viewed exactly straight from the front. One character, whole body, centered on a square pure-white background, occupying about 80% of image height. Arms extend diagonally down/out about 35 degrees from the torso, with clear white gaps between arms and belly. Legs straight, feet slightly apart, weight even, both flat soles on the same baseline. Empty relaxed rounded hands, no sword, no props.
Identity constraints: large round bald head, NO horns, no added hairstyle, one strong continuous dark-brown brow bar above the half-lidded deadpan eyes; cream projecting rounded muzzle with simple small nostrils and flat mouth; broad ears with pink inner ears; short stocky arms and legs; rounded protruding yellow belly, no shirt; plain dark-brown shorts, brown belt and the small square brass buckle already present in the reference; brown cloven hoof feet. Preserve the reference's head-to-body ratio and stocky proportions. A short thin yellow tail with a dark-brown tuft remains attached at the back; from the front it may peek just outside a hip, but must not become a belt or a second appendage. Yellow mitten-like hands follow the approved character, not realistic human hands.
Style/medium: clean smooth-edged 2D cartoon production drawing, flat local colors, restrained dark-brown contour lines, large readable color regions. Preserve the approved warm golden yellow, pale cream, muted pink and brown. No pixel stair steps in this modeling input; the game pixel conversion happens later. Pure solid white (#FFFFFF) background, uniform ambient illumination, no gradients, no cast shadow, no floor, no contact shadow, no rim light, no texture, no fur, no 3D-render gloss.
Camera constraints: orthographic true front, no three-quarter view, no perspective, head/body/pelvis facing directly forward, level camera. Both ears, both arms and both legs readable. No weapons, horns, new clothing, decorations, text, labels, watermark, multiple panels or other views.

## 纯侧面 / side_attempt01

Use case: stylized-concept. Asset: ONE pure orthographic RIGHT-FACING SIDE full-body modeling reference for reconstruction of the same Niulai character. Image 1 is the selected FRONT A-pose reference: it is the primary authority for identity, outfit, body proportions, color and vertical landmark heights. Image 2 is the approved original illustration, supporting the protruding muzzle and side silhouette; ignore its weapon and fighting stance. Image 3 is the approved pixel sprite color/silhouette reference; do not copy its pixelation or pose. Rotate the character of Image 1 by exactly 90 degrees, keeping the SAME neutral A pose, to show its exact pure side profile, facing screen-right. Head, torso, pelvis and feet all pure profile; no three-quarter turn and no visible far eye. Maintain the large round bald hornless head (~40% of standing height), pale cream protruding rounded muzzle, one thick continuous dark-brown brow bar (only its near-side profile is visible), one deadpan half-lidded near eye, pink inner ear, short stocky limbs, rounded protruding yellow belly, plain brown shorts, brown belt/small brass buckle, brown cloven hoof feet, and short thin yellow tail emerging behind the back of the shorts with dark-brown tuft. Preserve exact proportions of the front image; do not stretch or shrink the head, make limbs longer, slim the belly or increase the height of the shorts. A pose is the SAME 3D pose as the front image: both arms extend diagonally down/out to the sides about 35 degrees from torso, hands empty and relaxed, both legs straight with lateral separation, standing evenly with soles on one baseline. In a true side projection the left/right limbs naturally overlap; respect this instead of rotating the torso or drawing extra arms, spreading legs forward/back or inventing extra limbs. The near arm/hand must have a readable outline distinct from the rounded belly. Clean smooth-edged 2D production drawing with solid flat local colors, dark-brown thin contours, warm golden-yellow skin, cream muzzle, pink ear interior, brown shorts, belt and hooves. No perspective, no gradients, no lighting effects, no contact or cast shadow, no floor, no texture, no fur, no glossy 3D look. Pure uniform white #FFFFFF square background, centered, full-body visible, top/bottom margins like Image 1 and matching its character height (about 80-85% of square). No sword or other props, no horns/hair, no added clothing, no text, labels, watermark, multiple panels or other views.

## 尝试记录

实际共 4 次内置 image_gen 调用：正面 2 次，侧面 2 次。没有调用 MiniMax、Seedance 或外部 API。

| 次数 | 任务 | 输出 | 结果 |
| --- | --- | --- | --- |
| 1 | front_attempt01 | `attempts/niulai_front_attempt01.png` | A 姿势成立，但两条眉毛、渐变较明显，未选用 |
| 2 | front_attempt02 | `niulai_front_apose_v01.png` | 合并为一条粗眉，减少阴影，选用 |
| 3 | side_attempt01 | `attempts/niulai_side_attempt01.png` | 纯侧视成立，头高/腰线与正面略有差异，未选用 |
| 4 | side_attempt02 | `niulai_side_apose_v01.png` | 针对头高、肩/腰线、脚底修订后选用 |

## 正面修订 / front_attempt02

Use case: precise-object-edit. Edit target: the attached front A-pose Niulai modeling reference. Make exactly these two corrections: (1) replace the TWO separated eyebrows with ONE single continuous thick dark-brown horizontal brow bar across the brow area, matching the established single-brow character design; keep the same half-lidded deadpan eyes below. (2) Flatten all colors into uniform solid local-color regions, including yellow skin, pink ear interiors, cream muzzle, shorts, belt and hooves. Remove all smooth gradients, highlights, ambient occlusion, soft shadows and ground/contact shadows. Background must be uniform pure white #FFFFFF. Flat unlit 2D model-reference drawing, dark brown clean contour lines. Preserve the character identity, exact front orthographic camera, whole-body framing, head/body proportions, A-pose arms, leg separation, round belly, hornless round bald head, muzzle shape, ears, yellow mitten hands, brown shorts/belt/square buckle/cloven hoof feet, and the short thin yellow tail with dark brown tuft. Do not add horns, hair, sword, props, text, texture, realistic fur or further views. Keep everything else unchanged.

## 侧面修订 / side_attempt02

Use case: precise-object-edit. Image 1 is the edit target, a RIGHT-FACING PURE SIDE modeling view of Niulai. Image 2 is the selected FRONT modeling view and is the authority for vertical proportions. Make one targeted proportion correction to Image 1: align its vertical body landmarks with Image 2. Keep the top of the head at about 7% of canvas height and the bottom of the hoof soles at 92%; increase the side head's vertical height downward by about 8%, so its chin/neck join lands at about 40-41% of canvas height, matching Image 2; bring the shoulders down to that same head/body join. Place the TOP of the shorts/belt near 59% of canvas height and the shorts hem near 74%, matching Image 2. Let the lower legs be slightly shorter to preserve the same sole baseline. Keep the fingertips near 67% height. Do not make the character taller overall and do not change its pure side camera. Preserve the side-profile depth of the round head, cream protruding muzzle, rounded potbelly, tail and ear, the same single visible near eye and strong thick brown brow, hornless bald head, plain brown shorts, belt, square brass buckle, yellow mitten hands, brown hoof feet and tail dark tuft. Preserve the A pose of Image 2 viewed in pure profile: left/right arms and legs overlap naturally, with readable near arm outline. The result must remain EXACTLY pure orthographic SIDE facing right, never three-quarter or a second eye. Clean flat solid color model-reference drawing, no gradients or shading, uniform pure white #FFFFFF backdrop. No floor/contact/cast shadow. No sword, props, horns, hair, extra limbs, text or other views. One centered full-body character; keep the current margins and framing. Match the selected front's colors, contour style and identity.

## 原始工具输出

内置生图原文件留在 `C:/Users/Administrator/.codex/generated_images/01a13f04-7428-7ba2-a537-9980eae2b455/`；最终选图已复制到本项目，本机生图目录不是接手必需项。

- 第 1 次：`exec-3ea2a5e7-7861-40ee-b824-e87807a088d3.png`
- 第 2 次：`exec-fb749b99-140f-432f-bae6-cdbe8bb62bef.png`
- 第 3 次：`exec-0a0dbf5d-da94-49fd-8258-5d23252261dc.png`
- 第 4 次：`exec-edbc8ae7-ca21-47cb-a659-f729314c68c6.png`
