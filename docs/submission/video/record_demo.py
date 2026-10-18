"""Record the ~2-minute platform demo with headless Chrome (CDP screencast) and ffmpeg.

Needs: Google Chrome, ffmpeg on PATH (or FFMPEG=...), `pip install websocket-client`, and the SSH tunnel to the
demo container (BASE, default http://localhost:18000). Warm the caches first (one load of /, /predict, /go and a
Trishuli prediction scenario). Output: out/demo.mp4 (1920x1080, 30 fps, no audio) + out/segments/*.mp4 + out/shots.txt
with each segment's start time, for narration.

    python docs/submission/video/record_demo.py
"""
import base64, json, math, os, pathlib, shutil, subprocess, sys, tempfile, threading, time, urllib.request
import websocket

HERE = pathlib.Path(__file__).resolve().parent
BASE = os.environ.get("BASE", "http://localhost:18000")   # the demo container (or a test port)
OUT = pathlib.Path(os.environ.get("OUT", HERE / "out"))
CHROME = os.environ.get("CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
FFMPEG = os.environ.get("FFMPEG", shutil.which("ffmpeg") or "ffmpeg")
FFPROBE = str(pathlib.Path(FFMPEG).with_name("ffprobe" + pathlib.Path(FFMPEG).suffix)) if os.sep in FFMPEG or "/" in FFMPEG else "ffprobe"
FPS = 30

# cursor + tap ripple + chapter chip, injected into every page (headless Chrome draws no cursor)
OVERLAY = r"""
(() => { if (window.__ov) return; window.__ov = 1;
  const add = () => {
    const st = document.createElement('style');
    st.textContent = `#__cur{position:fixed;left:0;top:0;width:22px;height:22px;z-index:2147483647;pointer-events:none;transform:translate(-3px,-2px);transition:opacity .2s}
      #__cur.touch{width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.35);border:2px solid rgba(0,0,0,.55);transform:translate(-17px,-17px)}
      .__rip{position:fixed;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;border:3px solid #ffb000;z-index:2147483646;pointer-events:none;animation:__r .55s ease-out forwards}
      @keyframes __r{to{transform:scale(4.2);opacity:0}}
      #__chip{position:fixed;left:50%;top:12px;transform:translateX(-50%);white-space:nowrap;z-index:2147483647;pointer-events:none;font:600 15px/1.2 system-ui,Segoe UI,sans-serif;color:#fff;background:rgba(15,98,254,.92);padding:7px 12px;border-radius:999px;box-shadow:0 2px 10px #0005;opacity:0;transition:opacity .3s}`;
    document.head.appendChild(st);
    const c = document.createElement('div'); c.id = '__cur';
    c.innerHTML = '<svg viewBox="0 0 22 22" width="22" height="22"><path d="M2 1l16 9-7 2-3 7z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.body.appendChild(c);
    const chip = document.createElement('div'); chip.id = '__chip'; document.body.appendChild(chip);
    addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', e => { const r = document.createElement('div'); r.className = '__rip'; r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px'; document.body.appendChild(r); setTimeout(() => r.remove(), 700); }, true);
  };
  if (document.body) add(); else addEventListener('DOMContentLoaded', add);
  window.__chip = t => { const ch = document.getElementById('__chip'); if (ch) { ch.textContent = t; ch.style.opacity = t ? 1 : 0; } };
  window.__touch = on => { const c = document.getElementById('__cur'); if (c) { c.classList.toggle('touch', on); c.innerHTML = on ? '' : c.innerHTML; } };
})();
"""


class Chrome:
    def __init__(self, port=9339):
        self.prof = tempfile.mkdtemp(prefix="demo-chrome-")
        self.p = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={self.prof}",
                                   "--window-size=1280,720", "--hide-scrollbars", "--no-first-run", "--force-color-profile=srgb",
                                   "--remote-allow-origins=*", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json")); break
            except Exception:
                time.sleep(0.3)
        page = [t for t in tabs if t["type"] == "page"][0]
        self.ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=300, suppress_origin=True)
        self.lock, self.n, self.waiting, self.frames, self.rec = threading.Lock(), 0, {}, [], False
        threading.Thread(target=self._read, daemon=True).start()
        for m in ("Page.enable", "Runtime.enable", "Network.enable"):
            self.cmd(m)
        self.cmd("Page.addScriptToEvaluateOnNewDocument", source=OVERLAY)
        self.mx, self.my = 640, 360

    def _read(self):
        while True:
            try:
                m = json.loads(self.ws.recv())
            except Exception:
                return
            if m.get("method") == "Page.screencastFrame":
                p = m["params"]
                if self.rec:
                    self.frames.append((p["metadata"]["timestamp"] - self.offset, base64.b64decode(p["data"])))
                self._send({"id": 0, "method": "Page.screencastFrameAck", "params": {"sessionId": p["sessionId"]}}, wait=False)
            elif "id" in m and m["id"] in self.waiting:
                self.waiting[m["id"]][1] = m; self.waiting[m["id"]][0].set()

    def _send(self, msg, wait=True):
        with self.lock:
            if wait:
                self.n += 1; msg["id"] = self.n; ev = [threading.Event(), None]; self.waiting[self.n] = ev
            self.ws.send(json.dumps(msg))
        if wait:
            ev[0].wait(300); m = ev[1]; self.waiting.pop(msg["id"], None)
            if m is None or "error" in m:
                raise RuntimeError(f"{msg['method']}: {m and m.get('error')}")
            return m.get("result", {})

    def cmd(self, method, **params):
        return self._send({"method": method, "params": params})

    def js(self, expr):
        r = self.cmd("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r:
            raise RuntimeError(f"JS: {r['exceptionDetails'].get('exception', {}).get('description')}")
        return r.get("result", {}).get("value")

    def until(self, expr, timeout=120):
        t = time.time()
        while time.time() - t < timeout:
            try:
                if self.js(expr):
                    return
            except RuntimeError:
                pass
            time.sleep(0.25)
        raise TimeoutError(expr)

    def device(self, w, h, scale, mobile=False):
        self.cmd("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=scale, mobile=mobile)
        self.cmd("Emulation.setTouchEmulationEnabled", enabled=mobile)

    def go(self, url):
        self.cmd("Page.navigate", url=url)

    # ---- input with a visible cursor ----
    def move(self, x, y, dur=0.6):
        x0, y0, t0 = self.mx, self.my, time.time()            # time-based, so CDP latency never stretches a move
        while True:
            k = min(1.0, (time.time() - t0) / dur); e = k * k * (3 - 2 * k)
            self.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=x0 + (x - x0) * e, y=y0 + (y - y0) * e)
            if k >= 1: break
            time.sleep(0.012)
        self.mx, self.my = x, y

    def click(self, x, y, dur=0.6, pause=0.15):
        self.move(x, y, dur); time.sleep(pause)
        self.cmd("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1)
        time.sleep(0.06)
        self.cmd("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button="left", clickCount=1)

    def drag(self, x1, y1, x2, y2, dur=4.0):
        self.move(x1, y1, 0.5)
        self.cmd("Input.dispatchMouseEvent", type="mousePressed", x=x1, y=y1, button="left", clickCount=1)
        t0 = time.time()
        while True:
            k = min(1.0, (time.time() - t0) / dur)
            self.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=x1 + (x2 - x1) * k, y=y1 + (y2 - y1) * k, button="left", buttons=1)
            if k >= 1: break
            time.sleep(0.02)
        self.cmd("Input.dispatchMouseEvent", type="mouseReleased", x=x2, y=y2, button="left", clickCount=1)
        self.mx, self.my = x2, y2

    def center(self, sel):
        return self.js(f"(() => {{ const r = document.querySelector({json.dumps(sel)}).getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }})()")

    def click_sel(self, sel, dur=0.7):
        if not self.js(f"(() => {{ const r = document.querySelector({json.dumps(sel)}).getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }})()"):
            self.js(f"document.querySelector({json.dumps(sel)}).scrollIntoView({{block: 'center', behavior: 'smooth'}})"); time.sleep(0.8)
        x, y = self.center(sel); self.click(x, y, dur)

    def latlng_xy(self, lat, lon):
        return self.js(f"(() => {{ const p = map.latLngToContainerPoint([{lat}, {lon}]), r = map.getContainer().getBoundingClientRect(); return [r.x + p.x, r.y + p.y]; }})()")

    # ---- recording ----
    def start(self, chip=None, max_w=1920, max_h=1080):
        self.frames = []; self.rec = True; self.offset = 0.0
        self.cmd("Page.startScreencast", format="jpeg", quality=88, maxWidth=max_w, maxHeight=max_h, everyNthFrame=1)
        if chip:
            self.chip(chip)

    def chip(self, text):
        self.js(f"window.__chip && window.__chip({json.dumps(text)})")

    def pause(self):                                      # cut dead time (e.g. waiting for a cold computation)
        self.rec = False; self._paused = time.time()

    def resume(self):
        self.offset += time.time() - self._paused; self.rec = True

    def stop(self, name, pad=None):
        end = time.time() - self.offset
        self.cmd("Page.stopScreencast"); self.rec = False
        return encode(self.frames, name, pad, end)

    def close(self):
        try: self.ws.close()
        finally: self.p.terminate()


def encode(frames, name, pad=None, end=None):
    """Variable-rate screencast frames -> constant 30 fps 1920x1080 mp4 (each frame held until the next one)."""
    seg = OUT / "segments"; tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"seg-{name}-"))
    lines = []
    for i, (ts, jpg) in enumerate(frames):
        f = tmp / f"{i:05d}.jpg"; f.write_bytes(jpg)
        nxt = frames[i + 1][0] if i + 1 < len(frames) else max(end or 0, ts + 0.5)
        lines += [f"file '{f.as_posix()}'", f"duration {max(nxt - ts, 1 / FPS):.4f}"]
    lines.append(f"file '{(tmp / f'{len(frames) - 1:05d}.jpg').as_posix()}'")
    (tmp / "list.txt").write_text("\n".join(lines))
    vf = (f"scale=-2:1000,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0d1117" if pad == "phone"
          else "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black")
    out = seg / f"{name}.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-vf", vf + f",fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(out)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    dur = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                               capture_output=True, text=True).stdout or 0)
    print(f"  {name}: {len(frames)} frames, {dur:.1f} s", flush=True)
    return out, dur


# ------------------------------------------------------------------ the demo
def seg_terminal(c):
    c.device(1280, 720, 1.5)
    c.go((HERE / "term.html").as_uri()); c.until("document.readyState === 'complete'")
    c.js("document.getElementById('__cur') && (document.getElementById('__cur').style.opacity = 0)")
    c.start("Live on IBM LinuxONE · z17 · one container")
    c.until("window.done === true", 60); time.sleep(1.2)
    return c.stop("1-linuxone")


def seg_planner(c):
    c.device(1280, 720, 1.5)
    c.go(BASE + "/"); c.until("typeof DATA !== 'undefined' && DATA && document.querySelectorAll('.trig').length > 1", 120)
    time.sleep(2.5)                                                      # tiles
    c.start("Planner · for district officials")
    time.sleep(1.0)
    c.click_sel('.trig[data-t="03:30"]'); time.sleep(2.2)
    c.click_sel('.trig[data-t="06:40"]'); time.sleep(1.6)
    c.js("void map.flyTo([28.33, 84.90], 12, {duration: 1.5})"); time.sleep(2.2)    # the upper valley, where it hits first
    c.chip("Wave clock: the first wave moves down the river")
    c.js("document.getElementById('slider').scrollIntoView({block: 'center', behavior: 'smooth'})"); time.sleep(0.6)
    sx, sy = c.center("#slider"); w = c.js("document.getElementById('slider').getBoundingClientRect().width")
    c.drag(sx - w / 2 + 6, sy, sx - w / 2 + 6 + (w - 12) * 0.45, sy, 3.5); time.sleep(0.6)
    c.chip("AI damage model: P(destroyed) per building and bridge")
    c.click_sel("#m_dmg"); time.sleep(2.4)
    c.chip("New report: a flood starts upstream, computed on LinuxONE")
    c.click_sel("#pick", 0.5); time.sleep(0.3)
    lat, lon = c.js("(() => { const s = DATA.path.properties.stations, cs = DATA.path.geometry.coordinates; let i = s.findIndex(x => x.km >= 14); return [cs[i][1], cs[i][0]]; })()")
    x, y = c.latlng_xy(lat, lon); c.click(x, y, 0.8); time.sleep(1.5)
    c.pause(); c.until("document.getElementById('pickmsg').textContent.indexOf('Computing') < 0", 60); c.resume(); time.sleep(2.2)
    c.chip("Ranked alerts: one SMS each in English and Nepali")
    c.click_sel(".s[data-i='0']", 0.6); time.sleep(5.0)
    return c.stop("2-planner")


def seg_predict(c):
    c.device(1280, 720, 1.5)
    c.go(BASE + "/predict"); c.until("typeof sid !== 'undefined' && sid", 180); time.sleep(3)
    c.start("Where should I go? · any spot, any time after the burst")
    time.sleep(1.0)
    lat, lon = 28.2955, 84.9059                                          # Dobhan, a riverside settlement
    c.js(f"void map.setView([{lat}, {lon}], 15, {{animate: true}})"); time.sleep(2.0)
    x, y = c.latlng_xy(lat, lon); c.click(x, y, 0.9)
    c.until("raw && raw.status", 30); time.sleep(3.5)
    c.chip("Later: the flood started 20 minutes ago")
    sx, sy = c.center("#t"); w = c.js("document.getElementById('t').getBoundingClientRect().width")
    x0 = sx - w / 2 + 8
    c.drag(x0, sy, x0 + (w - 16) * 20 / 240, sy, 1.0); time.sleep(3.5)
    return c.stop("3-predict")


def seg_go(c):
    c.device(390, 844, 2, mobile=True)
    url = BASE + "/go?lat=28.2955&lon=84.9059&t=10"
    c.go(url); c.until("typeof ans !== 'undefined' && ans && ans.status", 60)
    c.until("navigator.serviceWorker.controller !== null", 20)            # offline cache armed
    c.go(url); c.until("typeof ans !== 'undefined' && ans && ans.status", 60); time.sleep(2.5)
    c.js("window.__touch && window.__touch(true)")
    c.mx, c.my = 195, 600
    c.start("Go · for someone in a panic", max_w=1080, max_h=1920)
    time.sleep(3.5)
    c.click_sel("#lang", 0.7); time.sleep(3.2)
    c.click_sel("#lang", 0.5); time.sleep(1.0)
    c.chip("Network down: still works offline")
    c.cmd("Network.emulateNetworkConditions", offline=True, latency=0, downloadThroughput=-1, uploadThroughput=-1)
    c.pause(); c.go(url); c.until("typeof ans !== 'undefined' && ans && ans.status", 30)
    try: c.until("document.querySelectorAll('.leaflet-tile-loaded').length > 6", 6)
    except TimeoutError: pass
    time.sleep(0.4); c.resume()
    c.js("window.__touch && window.__touch(true)"); c.chip("Network down: still works offline"); time.sleep(3.5)
    c.chip("Reached the green flag: safe")
    lat, lon = c.js("[goal(ans).lat, goal(ans).lon]")
    x, y = c.latlng_xy(lat, lon); c.click(x + 3, y + 3, 1.0); time.sleep(3.5)
    c.cmd("Network.emulateNetworkConditions", offline=False, latency=0, downloadThroughput=-1, uploadThroughput=-1)
    return c.stop("4-go", pad="phone")


def seg_architecture(c):
    c.device(1280, 720, 1.5)
    c.cmd("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])
    arch = HERE.parent.parent / "architecture.html"
    c.go(arch.as_uri()); c.until("document.readyState === 'complete'"); time.sleep(1.5)
    c.js("document.getElementById('__cur').style.opacity = 0; document.getElementById('deploy').scrollIntoView()")
    c.js("scrollBy(0, 150)"); time.sleep(0.5)
    c.start("Architecture: one container on LinuxONE")
    time.sleep(4.0)
    c.js("document.getElementById('linuxone').querySelector('figure').scrollIntoView({behavior: 'smooth', block: 'center'})")
    time.sleep(4.5)
    return c.stop("5-architecture")


def main():
    (OUT / "segments").mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] or ["terminal", "planner", "predict", "go", "architecture"]
    segs = {"terminal": seg_terminal, "planner": seg_planner, "predict": seg_predict, "go": seg_go, "architecture": seg_architecture}
    for name in only:
        c = Chrome()                                                     # fresh profile per segment
        try:
            print(f"recording {name}…", flush=True); segs[name](c)
        finally:
            c.close()
    files = sorted((OUT / "segments").glob("*.mp4"))
    (OUT / "concat.txt").write_text("\n".join(f"file '{f.as_posix()}'" for f in files))
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "concat.txt"),
                    "-c", "copy", "-movflags", "+faststart", str(OUT / "demo.mp4")], check=True)
    t, rows = 0.0, []
    for f in files:
        d = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                 capture_output=True, text=True).stdout)
        rows.append(f"{int(t // 60)}:{t % 60:04.1f}  {f.stem}  ({d:.1f} s)"); t += d
    rows.append(f"total {t:.1f} s")
    (OUT / "shots.txt").write_text("\n".join(rows) + "\n"); print("\n".join(rows))


if __name__ == "__main__":
    main()
