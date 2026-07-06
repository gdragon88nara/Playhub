"""Starter templates. Every new project comes with default config code already
in place so a developer can hit Run / Deploy immediately."""

# HTML/Three.js browser game — deploys straight to a playable Game.
HTML_GAME = [
    ("index.html", """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>My Game</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <canvas id="game" width="640" height="360"></canvas>
  <script src="main.js"></script>
</body>
</html>
"""),
    ("style.css", """html, body { margin: 0; background: #0a0a0a; display: grid; place-items: center; height: 100%; }
#game { image-rendering: pixelated; border: 1px solid #222; }
"""),
    ("main.js", """const c = document.getElementById("game");
const ctx = c.getContext("2d");
let x = 0;
function loop() {
  ctx.fillStyle = "#0a0a0a"; ctx.fillRect(0, 0, c.width, c.height);
  ctx.fillStyle = "#6366f1"; ctx.fillRect(x % c.width, 160, 40, 40);
  x += 2;
  requestAnimationFrame(loop);
}
loop();
"""),
]

# Story game — scenes advance automatically on completion.
STORY_GAME = [
    ("scene_0.html", """<!doctype html>
<html lang="en"><head><meta charset="utf-8" />
<style>html,body{margin:0;height:100%;display:grid;place-items:center;background:#0a0a0a;color:#eee;font-family:sans-serif}</style>
</head><body>
  <div style="text-align:center">
    <h1>Scene 1</h1>
    <p>Your story begins. Click to continue.</p>
    <button onclick="nextScene()">Continue</button>
  </div>
  <script src="scene.js"></script>
</body></html>
"""),
    ("scene_1.html", """<!doctype html>
<html lang="en"><head><meta charset="utf-8" />
<style>html,body{margin:0;height:100%;display:grid;place-items:center;background:#0a0a0a;color:#eee;font-family:sans-serif}</style>
</head><body>
  <div style="text-align:center">
    <h1>Scene 2</h1>
    <p>The next chapter. The end.</p>
    <button onclick="nextScene()">Finish</button>
  </div>
  <script src="scene.js"></script>
</body></html>
"""),
    ("scene.js", """// Advancing a scene: tell the platform player to load the next one.
function nextScene() {
  window.parent.postMessage({ type: "gameplatform:next-scene" }, "*");
}
"""),
]

# Python program — runs in the terminal with `python main.py`.
PYTHON = [
    ("main.py", """def main():
    print("Hello from your game platform project!")
    for i in range(3):
        print("tick", i)


if __name__ == "__main__":
    main()
"""),
    ("requirements.txt", "# add your Python dependencies here, one per line\n"),
    ("README.md", "# My Project\n\nRun in the terminal with `python main.py`.\n"),
]

# WebGL game — GPU-accelerated fullscreen shader. Self-contained (no CDN), so it
# runs in the live webview instantly and demonstrates the engine's performance
# path: everything below is drawn by the GPU each frame.
WEBGL_GAME = [
    ("index.html", """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WebGL Game</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <canvas id="gl"></canvas>
  <script src="main.js"></script>
</body>
</html>
"""),
    ("style.css", """html, body { margin: 0; height: 100%; background: #000; overflow: hidden; }
#gl { display: block; width: 100vw; height: 100vh; }
"""),
    ("main.js", """// Minimal WebGL renderer: a fullscreen quad shaded on the GPU every frame.
const canvas = document.getElementById("gl");
const gl = canvas.getContext("webgl");
if (!gl) { document.body.innerHTML = "WebGL not supported"; }

const VERT = `attribute vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }`;
const FRAG = `precision highp float;
uniform vec2 res; uniform float t;
void main(){
  vec2 uv = (gl_FragCoord.xy / res) * 2.0 - 1.0;
  uv.x *= res.x / res.y;
  float d = 0.0;
  for (int i = 0; i < 4; i++) {
    float fi = float(i);
    d += 0.15 / abs(length(uv + 0.4 * vec2(sin(t + fi), cos(t * 1.3 + fi))) - 0.3);
  }
  gl_FragColor = vec4(d * vec3(0.3, 0.5, 1.0), 1.0);
}`;

function compile(type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw gl.getShaderInfoLog(s);
  return s;
}
const prog = gl.createProgram();
gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG));
gl.linkProgram(prog); gl.useProgram(prog);

const buf = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, buf);
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 3,-1, -1,3]), gl.STATIC_DRAW);
const loc = gl.getAttribLocation(prog, "p");
gl.enableVertexAttribArray(loc);
gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

const uRes = gl.getUniformLocation(prog, "res");
const uT = gl.getUniformLocation(prog, "t");

function resize() {
  canvas.width = canvas.clientWidth; canvas.height = canvas.clientHeight;
  gl.viewport(0, 0, canvas.width, canvas.height);
}
window.addEventListener("resize", resize); resize();

const start = performance.now();
function frame() {
  gl.uniform2f(uRes, canvas.width, canvas.height);
  gl.uniform1f(uT, (performance.now() - start) / 1000);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
  requestAnimationFrame(frame);
}
frame();
"""),
]

# TypeScript game — authored in game.ts; the platform transpiles it to game.js
# for both the live preview and the deployed bundle (index.html loads game.js).
TYPESCRIPT_GAME = [
    ("index.html", """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>TypeScript Game</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <canvas id="game" width="640" height="360"></canvas>
  <!-- game.ts is compiled to game.js automatically -->
  <script src="game.js"></script>
</body>
</html>
"""),
    ("style.css", """html, body { margin: 0; height: 100%; background: #0a0a0a; display: grid; place-items: center; }
#game { border: 1px solid #222; background: #111; }
"""),
    ("game.ts", """interface Ball {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
}

const canvas = document.getElementById("game") as HTMLCanvasElement;
const ctx = canvas.getContext("2d")!;

const ball: Ball = { x: 320, y: 180, vx: 3, vy: 2.2, r: 16 };

function update(): void {
  ball.x += ball.vx;
  ball.y += ball.vy;
  if (ball.x - ball.r < 0 || ball.x + ball.r > canvas.width) ball.vx *= -1;
  if (ball.y - ball.r < 0 || ball.y + ball.r > canvas.height) ball.vy *= -1;
}

function draw(): void {
  ctx.fillStyle = "#0a0a0a";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#6366f1";
  ctx.beginPath();
  ctx.arc(ball.x, ball.y, ball.r, 0, Math.PI * 2);
  ctx.fill();
}

function loop(): void {
  update();
  draw();
  requestAnimationFrame(loop);
}

loop();
"""),
]

TEMPLATES = {
    "html_game": {"label": "HTML / Canvas game", "kind": "normal", "engine": "html", "files": HTML_GAME},
    "webgl_game": {"label": "WebGL game (GPU shader)", "kind": "normal", "engine": "html", "files": WEBGL_GAME},
    "typescript_game": {"label": "TypeScript game", "kind": "normal", "engine": "html", "files": TYPESCRIPT_GAME},
    "story_game": {"label": "Story game (scenes)", "kind": "story", "engine": "html", "files": STORY_GAME},
    "python": {"label": "Python program", "kind": "code", "engine": "html", "files": PYTHON},
}
