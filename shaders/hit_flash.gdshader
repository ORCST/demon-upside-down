shader_type canvas_item;
// 受击闪白 / 蓄力染色：把颜色往 flash_color 混合，透明度保持不变

uniform vec4 flash_color : source_color = vec4(1.0);
uniform float flash_amount : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	COLOR = vec4(mix(COLOR.rgb, flash_color.rgb, flash_amount), COLOR.a);
}
