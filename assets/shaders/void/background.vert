#version 330

in vec2 vert;
out vec2 uv;

void main() {
    uv = (vert + 1.0) / 2.0;
    gl_Position = vec4(vert, 0.0, 1.0);
}
