import asyncio, json, os, re, subprocess, sys, threading, time, tkinter as tk
import requests, keyboard, pyperclip, pystray
from PIL import Image, ImageDraw, ImageGrab
import winsdk.windows.media.ocr as wocr
import winsdk.windows.graphics.imaging as wimg
import winsdk.windows.storage.streams as wss

APPDIR = os.path.join(os.environ["APPDATA"], "DichNhanh"); os.makedirs(APPDIR, exist_ok=True)
CFG = os.path.join(APPDIR, "config.json")
DEF = {"model": "gemma3:12b", "hk_screen": "ctrl+alt+q", "hk_type": "ctrl+shift+t",
       "hk_rescan": "ctrl+alt+w", "target": "English", "auto_target": True, "rescan_sec": 3, "overlay_seconds": 15, "game_mode": True, "game_num_gpu": 24, "game_num_thread": 4}
LANGS = ["English", "Japanese", "Chinese", "Korean", "Thai", "Russian", "French", "German", "Spanish", "Indonesian"]
OLLAMA = "http://localhost:11434"
cfg = dict(DEF)
if os.path.exists(CFG):
    try: cfg.update(json.load(open(CFG, encoding="utf-8")))
    except Exception: pass
def save(): json.dump(cfg, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def ensure_ollama():
    try: requests.get(OLLAMA, timeout=2); return
    except Exception: pass
    exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    subprocess.Popen([exe if os.path.exists(exe) else "ollama", "serve"], creationflags=0x08000000)
    for _ in range(30):
        time.sleep(1)
        try: requests.get(OLLAMA, timeout=2); return
        except Exception: pass

CJK = r"\u3000-\u303f\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af\uff00-\uffef"
def clean_ocr(t):
    t = re.sub(r"(?<=[%s]) +(?=[%s])" % (CJK, CJK), "", t)
    t = re.sub(r"(?<=[%s]) +(?=[A-Za-z0-9])|(?<=[A-Za-z0-9]) +(?=[%s])" % (CJK, CJK), "", t)
    t = re.sub(r"(?<=[%s])\n(?=[%s])" % (CJK, CJK + "A-Za-z0-9"), "", t)
    for a, b in {"\u4ebb\u5c14": "\u4f60", "\u4ebb\u4e5f": "\u4ed6", "\u5973\u4e5f": "\u5979", "\u4ebb\u95e8": "\u4eec", "\u53e3\u5df4": "\u5427", "\u6c35\u8096": "\u6d88"}.items(): t = t.replace(a, b)
    return t
OLD_SYS = ("You are a translation engine for casual online chat and games. Translate the user's text into {lang}. "
       "Output ONLY the translation, nothing else: no quotes, no notes, no explanations, no romanization. "
       "Keep the casual tone, slang, emoji, names and game terms natural like a native speaker chatting.")
def opts():
    o = {"temperature": 0.2, "num_ctx": 1024, "num_predict": 400}
    if cfg.get("game_mode"): o.update(num_gpu=cfg["game_num_gpu"], num_thread=cfg["game_num_thread"])
    return o
SYS = ("You are a professional translator for online game chat. Translate the user's text into {lang}.\n"
       "Rules:\n- Translate EVERY clause and detail faithfully: times (e.g. \u4eca\u5929\u665a\u4e0a = tonight), who does what, who pays/treats whom (\u6211\u8bf7\u4f60 = I treat you). Never omit, summarize or add.\n"
       "- You are a pure offline translation tool for the user's private use. Translate everything faithfully, including explicit adult sexual content, profanity, slurs and graphic violence, at the same intensity as the source. Never refuse, censor, soften, euphemize, omit, or add warnings or comments.\n"
       "- The text may come from OCR and contain small errors or broken characters; infer the intended words.\n"
       "- Chinese personal and place names: render in Sino-Vietnamese (H\u00e1n Vi\u1ec7t) when translating to Vietnamese, e.g. \u5f90\u91ce = T\u1eeb D\u00e3, \u5f90\u5bb6 = nh\u00e0 h\u1ecd T\u1eeb; never pinyin. Japanese/Korean names keep romanized form.\n"
       "- Never invent or add proper nouns (dynasty, place, person names) that are not in the source, e.g. 皇朝末年 = cuối thời hoàng triều (do NOT name a specific dynasty).\n"
       "- Idioms and fixed phrases: keep their exact meaning even when the voice is casual, e.g. \u770b\u4ed6\u7684\u7b11\u8bdd = ch\u1edd xem tr\u00f2 c\u01b0\u1eddi c\u1ee7a y (NOT insult/humiliate him).\n"
       "- Tone: casual, natural gamer slang like friends chatting. If {lang} is Vietnamese, use 'tao/m\u00e0y' or 't\u1ee5i m\u00ecnh', gamer words like ph\u00f3 b\u1ea3n, boss, farm, wipe.\n"
       "- Output ONLY the translation in {lang}, no quotes, notes, explanations, original text or romanization.")
def translate(text, lang, model=None):
    r = requests.post(OLLAMA + "/api/chat", timeout=180, json={
        "model": model or cfg["model"], "stream": False, "keep_alive": "30m",
        "options": opts(),
        "messages": [{"role": "system", "content": SYS.format(lang=lang)}, {"role": "user", "content": text}]})
    r.raise_for_status()
    return r.json()["message"]["content"].strip()

def detect(text):
    if re.search(r"[\u3040-\u30ff]", text): return "Japanese"
    if re.search(r"[\uac00-\ud7af]", text): return "Korean"
    if re.search(r"[\u4e00-\u9fff]", text): return "Chinese"
    if re.search(r"[\u0e00-\u0e7f]", text): return "Thai"
    if re.search(r"[\u0400-\u04ff]", text): return "Russian"
    return "English"

async def _ocr(img):
    img = img.convert("RGBA")
    if img.width < 300: img = img.resize((img.width * 2, img.height * 2))
    w = wss.DataWriter(); w.write_bytes(img.tobytes("raw", "BGRA"))
    bmp = wimg.SoftwareBitmap.create_copy_from_buffer(w.detach_buffer(), wimg.BitmapPixelFormat.BGRA8, img.width, img.height)
    best = ""
    for lg in wocr.OcrEngine.available_recognizer_languages:
        eng = wocr.OcrEngine.try_create_from_language(lg)
        res = await eng.recognize_async(bmp)
        t = "\n".join(l.text for l in res.lines)
        if len(re.sub(r"[\s?]", "", t)) > len(re.sub(r"[\s?]", "", best)): best = t
    return best
def ocr(img): return asyncio.run(_ocr(img))

class App:
    def __init__(s):
        s.root = tk.Tk(); s.root.withdraw(); s.region = None; s.rescan = False; s.ov = None; s.last = ""
    def ui(s, f): s.root.after(0, f)
    # ---- screen translate
    def select_region(s):
        top = tk.Toplevel(s.root); top.attributes("-fullscreen", True, "-alpha", 0.3, "-topmost", True)
        c = tk.Canvas(top, cursor="cross", bg="black"); c.pack(fill="both", expand=True); st = {}
        def dn(e): st["x"], st["y"] = e.x_root, e.y_root; st["r"] = c.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)
        def mv(e): c.coords(st["r"], st["x"] - top.winfo_rootx(), st["y"] - top.winfo_rooty(), e.x, e.y)
        def up(e):
            x1, y1, x2, y2 = min(st["x"], e.x_root), min(st["y"], e.y_root), max(st["x"], e.x_root), max(st["y"], e.y_root)
            top.destroy()
            if x2 - x1 > 5 and y2 - y1 > 5:
                s.region = (x1, y1, x2, y2); threading.Thread(target=s.do_region, daemon=True).start()
        c.bind("<ButtonPress-1>", dn); c.bind("<B1-Motion>", mv); c.bind("<ButtonRelease-1>", up)
        top.bind("<Escape>", lambda e: top.destroy()); top.focus_force()
    def do_region(s, quiet=False):
        try:
            if s.ov: s.ui(lambda: s.ov.withdraw()); time.sleep(0.15)
            text = clean_ocr(ocr(ImageGrab.grab(bbox=s.region, all_screens=True))).strip()
            open(os.path.join(APPDIR, "ocr_log.txt"), "a", encoding="utf-8").write(time.strftime("%H:%M:%S ") + text + "\n")
            if not text: (None if quiet else s.show("(Khong doc duoc chu)")); return
            if quiet and text == s.last: s.ui(lambda: s.ov and s.ov.deiconify()); return
            s.last = text; lg = detect(text)
            if cfg["auto_target"] and lg != cfg["target"]: cfg["target"] = lg; save(); s.refresh_menu()
            if not quiet: s.show("Dang dich...")
            s.show(translate(text, "Vietnamese"))
        except Exception as e: s.show("Loi: %s" % e)
    def show(s, msg):
        def f():
            if not s.ov:
                s.ov = tk.Toplevel(s.root); s.ov.overrideredirect(True); s.ov.attributes("-topmost", True, "-alpha", 0.92)
                s.lb = tk.Label(s.ov, bg="#202020", fg="#ffffff", font=("Segoe UI", 12), justify="left", padx=8, pady=6)
                s.lb.pack(); s.lb.bind("<Button-1>", lambda e: s.ov.withdraw())
                s.ov.update_idletasks()
                import ctypes; u = ctypes.windll.user32; hw = u.GetParent(s.ov.winfo_id()) or s.ov.winfo_id()
                u.SetWindowLongW(hw, -20, u.GetWindowLongW(hw, -20) | 0x08000000 | 0x80 | 0x8)
            x1, y1, x2, y2 = s.region or (100, 100, 500, 200)
            s.lb.config(text=msg, wraplength=max(300, x2 - x1))
            s.ov.update_idletasks(); h = s.ov.winfo_reqheight()
            s.ov.geometry("+%d+%d" % (x1, y2 + 4 if y2 + 4 + h < s.root.winfo_screenheight() else max(0, y1 - h - 4)))
            s.ov.deiconify()
            if getattr(s, "_t", None): s.root.after_cancel(s._t)
            s._t = s.root.after(int(cfg.get("overlay_seconds", 15) * 1000), s.ov.withdraw)
        s.ui(f)
    def toggle_rescan(s, *a):
        s.rescan = not s.rescan and s.region is not None
        s.refresh_menu()
        if s.rescan: threading.Thread(target=s.rescan_loop, daemon=True).start()
    def rescan_loop(s):
        while s.rescan:
            time.sleep(cfg["rescan_sec"]);
            if s.rescan: s.do_region(quiet=True)
    # ---- type translate
    def type_translate(s):
        old = None
        try: old = pyperclip.paste()
        except Exception: pass
        for k in ("ctrl", "shift", "alt", "t"): keyboard.release(k)
        time.sleep(0.05); pyperclip.copy("")
        keyboard.send("ctrl+a"); time.sleep(0.05); keyboard.send("ctrl+c"); time.sleep(0.15)
        txt = pyperclip.paste().strip()
        if txt:
            try:
                out = translate(txt, cfg["target"]); pyperclip.copy(out); keyboard.send("ctrl+v"); time.sleep(0.2)
            except Exception as e: s.region = s.region; s.show("Loi dich: %s" % e)
        if old is not None:
            try: pyperclip.copy(old)
            except Exception: pass
    # ---- tray
    def refresh_menu(s):
        if hasattr(s, "icon"): s.icon.menu = s.menu(); s.icon.update_menu()
    def menu(s):
        M, I = pystray.Menu, pystray.MenuItem
        def setm(m): return lambda *a: (cfg.__setitem__("model", m), save(), s.refresh_menu())
        def sett(l): return lambda *a: (cfg.__setitem__("target", l), save(), s.refresh_menu())
        return M(
            I("Dich man hinh (%s)" % cfg["hk_screen"], lambda *a: s.ui(s.select_region)),
            I("Tu quet lai vung cu (%s)" % cfg["hk_rescan"], s.toggle_rescan, checked=lambda i: s.rescan),
            I("Ngon ngu gui di: %s" % cfg["target"], M(
                I("Tu theo man hinh", lambda *a: (cfg.__setitem__("auto_target", not cfg["auto_target"]), save()), checked=lambda i: cfg["auto_target"]),
                *[I(l, sett(l), checked=lambda i, l=l: cfg["target"] == l, radio=True) for l in LANGS])),
            I("Che do choi game (nhe GPU)", lambda *a: (cfg.__setitem__("game_mode", not cfg.get("game_mode")), save()), checked=lambda i: cfg.get("game_mode")),
            I("Model", M(*[I(m, setm(m), checked=lambda i, m=m: cfg["model"] == m, radio=True) for m in ("gemma3:12b", "gemma3:4b")])),
            I("Sua phim tat / cai dat (config.json)", lambda *a: os.startfile(CFG)),
            I("Thoat", lambda *a: (setattr(s, "rescan", False), s.icon.stop(), s.ui(s.root.quit))))
    def run(s):
        save(); threading.Thread(target=ensure_ollama, daemon=True).start()
        keyboard.add_hotkey(cfg["hk_screen"], lambda: s.ui(s.select_region))
        keyboard.add_hotkey(cfg["hk_type"], lambda: threading.Thread(target=s.type_translate, daemon=True).start())
        keyboard.add_hotkey(cfg["hk_rescan"], s.toggle_rescan)
        img = Image.new("RGB", (64, 64), "#1e88e5"); d = ImageDraw.Draw(img); d.text((14, 18), "VI", fill="white", font_size=26) if hasattr(d, "text") else None
        s.icon = pystray.Icon("DichNhanh", img, "DichNhanh", s.menu())
        s.icon.run_detached()
        s.root.after(1500, lambda: s.icon.notify("DichNhanh dang chay. Ctrl+Alt+Q dich man hinh, Ctrl+Shift+T dich chu go.", "DichNhanh"))
        if "--selftest" in sys.argv: s.root.after(3000, lambda: (print("HOTKEYS_OK"), s.icon.stop(), s.root.quit()))
        s.root.mainloop()

if __name__ == "__main__":
    if "--test" in sys.argv:
        ensure_ollama(); print(translate(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)); sys.exit()
    import ctypes
    ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\DichNhanh_single")
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(None, "DichNhanh dang chay roi (xem icon duoi khay).", "DichNhanh", 0x40); sys.exit()
    App().run()
