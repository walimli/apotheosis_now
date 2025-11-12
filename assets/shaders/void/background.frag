#version 330

uniform float time;
uniform vec2 resolution;
uniform vec2 camera_offset;
uniform vec2 scroll;
uniform float crt_effect;
uniform float saturation;
uniform bool in_void;
uniform float parallax_factor;

out vec4 f_color;
in vec2 uv;

float hash(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return -1.0 + 2.0 * fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453123);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    for (int i = 0; i < 4; i++) {
        value += amplitude * noise(p * frequency);
        frequency *= 2.0;
        amplitude *= 0.5;
    }
    return value;
}

vec3 palette(float n) {
    vec3 deep = vec3(0.02, 0.02, 0.03);
    vec3 mid = vec3(0.08, 0.03, 0.12);
    vec3 glow = vec3(0.35, 0.15, 0.45);
    vec3 edge = vec3(0.85, 0.55, 0.95);
    vec3 base = mix(deep, mid, smoothstep(0.0, 0.4, n));
    vec3 highlight = mix(glow, edge, smoothstep(0.4, 1.0, n));
    return mix(base, highlight, n);
}

vec3 apply_crt(vec3 color, vec2 frag_uv) {
    float vignette = smoothstep(0.9, 0.4, distance(frag_uv, vec2(0.5)));
    vec3 rgb_shift = vec3(
        color.r,
        color.g * (0.9 + 0.1 * sin(time * 2.0 + frag_uv.x * 20.0)),
        color.b * (0.9 + 0.1 * cos(time * 1.5 + frag_uv.y * 18.0))
    );
    return mix(color, rgb_shift * vignette, crt_effect);
}

void main() {
    vec2 pixel = uv * resolution;
    vec2 world_uv = (pixel + camera_offset * parallax_factor + scroll);
    world_uv *= 0.01;
    float animation = time * 0.08;
    float field = fbm(world_uv + vec2(animation, -animation * 0.73));
    float ripples = fbm(world_uv * 2.5 - vec2(animation * 1.3, animation * 0.8));
    float depth = smoothstep(-1.0, 1.0, field + ripples * 0.35);

    vec3 color = palette(depth);
    if (!in_void) {
        color = mix(color, vec3(0.0), 0.5);
    }

    color = apply_crt(color, uv);

    float luminance = dot(color, vec3(0.299, 0.587, 0.114));
    color = mix(vec3(luminance), color, clamp(saturation, 0.0, 1.0));

    f_color = vec4(color, 1.0);
}
