"""本地看图：把 glb 拖进浏览器看，不走 Unity 打包。

为什么：作者验收用 Unity（换 glb → 建场景 → 打包 235 MB → autoshot，约 6 min），
但你自查"净空/过道/悬空"根本不需要 URP。glb 只有 7.7 MB，浏览器 2 s 就能走。

口径：这里的材质是原始 glTF（无 URP / ACES），**只判关系，不判观感**。

用法：
    py -3 tools/audit/view.py                          # 自动找最新的精模 glb
    py -3 tools/audit/view.py --glb docs/assets/xxx.glb --port 8765
    py -3 tools/audit/view.py --open                   # 顺便开浏览器

按 `F` 切飞行模式（WASD + 鼠标），`O` 切回轨道模式。
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import socket
import subprocess
import sys
import threading
import webbrowser
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

try:                      # MSYS bash 里控制台是 UTF-8，Python 默认 cp936 会输出乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

HTML = """<!doctype html><meta charset="utf-8"><title>__TITLE__</title>
<style>
 html,body{margin:0;height:100%;background:#0b0d10;color:#cfd6e0;
   font:13px/1.5 "Segoe UI",system-ui,sans-serif;overflow:hidden}
 #hud{position:fixed;left:12px;top:10px;z-index:9;background:#0009;padding:8px 10px;
   border-radius:6px;pointer-events:none}
 kbd{background:#222a33;border-radius:3px;padding:0 4px;color:#9fd}
</style>
<div id="hud">__TITLE__ · <kbd>F</kbd> 飞行/WASD · <kbd>O</kbd> 轨道 · 拖拽看</div>
<script type="importmap">{"imports":{
 "three":"https://unpkg.com/three@0.160.0/build/three.module.js",
 "three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {DRACOLoader} from 'three/addons/loaders/DRACOLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const rn=new THREE.WebGLRenderer({antialias:true});
rn.setPixelRatio(devicePixelRatio);rn.setSize(innerWidth,innerHeight);
rn.toneMapping=THREE.ACESFilmicToneMapping;document.body.appendChild(rn.domElement);
const sc=new THREE.Scene();sc.background=new THREE.Color(0x0b0d10);
const cam=new THREE.PerspectiveCamera(55,innerWidth/innerHeight,0.1,5000);
cam.position.set(0,12,40);
sc.add(new THREE.HemisphereLight(0xbfd4ff,0x202024,2.2));
const dl=new THREE.DirectionalLight(0xffffff,2.0);dl.position.set(30,60,20);sc.add(dl);
const oc=new OrbitControls(cam,rn.domElement);oc.target.set(0,6,0);oc.enableDamping=true;
let fly=false;const key={};
addEventListener('keydown',e=>{key[e.code]=true;
  if(e.code==='KeyF'){fly=!fly;oc.enabled=!fly;}
  if(e.code==='KeyO'){fly=false;oc.enabled=true;}});
addEventListener('keyup',e=>{key[e.code]=false});
addEventListener('resize',()=>{cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();
  rn.setSize(innerWidth,innerHeight)});
let yaw=0,pitch=0;
rn.domElement.addEventListener('click',()=>{if(fly)rn.domElement.requestPointerLock()});
addEventListener('mousemove',e=>{if(fly&&document.pointerLockElement){
  yaw-=e.movementX*0.0022;pitch-=e.movementY*0.0022;
  pitch=Math.max(-1.5,Math.min(1.5,pitch));
  cam.rotation.set(pitch,yaw,0,'YXZ');}});
const draco=new DRACOLoader().setDecoderPath('https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/');
const VIEW=__VIEW__;
new GLTFLoader().setDRACOLoader(draco).load('__GLB__',g=>{
  sc.add(g.scene);const b=new THREE.Box3().setFromObject(g.scene);const c=b.getCenter(new THREE.Vector3());
  const s=b.getSize(new THREE.Vector3());
  if(VIEW&&VIEW.pos){cam.position.set(...VIEW.pos);oc.target.set(...VIEW.target);}
  else{oc.target.copy(c);cam.position.set(c.x-s.x*0.9,c.y+s.y*0.8,c.z-s.z*0.9);}
  oc.update();
  let n=0,tri=0;g.scene.traverse(o=>{if(o.isMesh){n++;tri+=o.geometry.index?
    o.geometry.index.count/3:o.geometry.attributes.position.count/3;}});
  document.getElementById('hud').textContent=
    `${n} 物体 / ${Math.round(tri).toLocaleString()} 三角面 · F 飞行 O 轨道`;
},undefined,e=>{document.getElementById('hud').textContent='加载失败：'+e});
const clock=new THREE.Clock();
rn.setAnimationLoop(()=>{const d=clock.getDelta();
  if(fly&&document.pointerLockElement){const v=42*d,f=new THREE.Vector3();
    cam.getWorldDirection(f);
    if(key.KeyW)cam.position.addScaledVector(f,v);
    if(key.KeyS)cam.position.addScaledVector(f,-v);
    const rt=new THREE.Vector3().crossVectors(f,cam.up).normalize();
    if(key.KeyD)cam.position.addScaledVector(rt,v);
    if(key.KeyA)cam.position.addScaledVector(rt,-v);
    if(key.KeyQ)cam.position.y+=v; if(key.KeyE)cam.position.y-=v;}
  else oc.update(); rn.render(sc,cam);});
</script>"""


def find_glb():
    pats = [os.path.join(ROOT, "docs", "assets", "*精模*.glb"),
            os.path.join(ROOT, "docs", "assets", "*.glb")]
    for p in pats:
        hits = sorted(glob.glob(p), key=os.path.getmtime, reverse=True)
        if hits:
            return hits[0]
    return None


def free_port(start=8765):
    for port in range(start, start + 40):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", default="")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--shot", default="池座坐姿",
                    help="站位预设（取 build_hall.py 的 SHOTS 名，默认池座坐姿）")
    ap.add_argument("--outside", action="store_true", help="不设机位，自动框全景")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    glb = args.glb or find_glb()
    if not glb or not os.path.exists(glb):
        print("找不到 glb，用 --glb 指定", file=sys.stderr)
        return 2

    stage = os.path.join(os.environ.get("TEMP", "."), "grandhall_view")
    os.makedirs(stage, exist_ok=True)
    shutil.copy2(glb, os.path.join(stage, "model.glb"))
    view = None
    if not args.outside:
        try:
            sys.path.insert(0, HERE)
            from shots_table import load_shots
            table = dict(load_shots())
            spec = table.get(args.shot)
            if spec is None:
                print(f"没有站位 {args.shot}，改用自动框景", file=sys.stderr)
            else:
                lx, ly, lz = spec["loc"]
                tx, ty, tz = spec["target"]
                view = {"pos": [lx, lz, -ly], "target": [tx, tz, -ty]}
        except Exception as exc:            # noqa: BLE001
            print(f"读站位失败（{exc}），改用自动框景", file=sys.stderr)

    title = os.path.basename(glb)
    import json as _json
    html = (HTML.replace("__GLB__", "model.glb").replace("__TITLE__", title)
                .replace("__VIEW__", _json.dumps(view)))
    with open(os.path.join(stage, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)

    port = args.port or free_port()
    handler = functools.partial(SimpleHTTPRequestHandler, directory=stage)
    srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"GLB  {glb}")
    print(f"URL  {url}   （Ctrl+C 结束；材质是原始 glTF，只判关系不判观感）")
    if args.open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
