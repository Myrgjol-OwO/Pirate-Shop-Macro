"""
PIRATE SHOP MACRO  -  windowed app (no console)
Fortnite auto-ready / return-to-lobby loop.

Cycle:
  1. Find READY and click it (gives up after READY_TIMEOUT).
  2. Every CHECK_INTERVAL seconds look for the NVIDIA Highlights button
     (and the fail-safe image, which gets clicked if found; 5s later it
     checks for READY again).
  3. On elimination: press Esc, click menu, click leave. Count a death. Repeat.

Images (cropped screenshots) go in an "images" folder next to this file / the exe:
  ready.png, nvidia.png, menu.png, leave.png, failsafe.png

Double-click this .pyw file to open the app. F8 stops the macro.
"""

import ctypes
import json
import math
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

import keyboard
import pyautogui

# ---------------- settings ----------------
CHECK_INTERVAL = 25        # seconds between "am I dead?" checks
CONFIDENCE = 0.8           # image match strictness (0-1); lower if it misses
LOBBY_WAIT = 10            # seconds to wait after leaving, before readying up
READY_RETRY = 2            # seconds between searches for the ready button
READY_TIMEOUT = 15         # give up on the ready button after this many seconds
STEP_DELAY = 1.0           # pause after Esc / after each click so menus can load
STEP_TIMEOUT = 10          # seconds to keep looking for menu / leave buttons
POLL_INTERVAL = 1.0        # seconds between searches while hunting for menu/leave
FAILSAFE_READY_DELAY = 5   # seconds after clicking fail-safe before checking ready
REMEMBER_PAD = 40          # pixels of padding around a remembered button location
START_DELAY = 5            # seconds after pressing Start before the macro begins
STOP_KEY = "f8"

# Search only where each button appears: (left, top, width, height). None = whole screen.
REGIONS = {"ready": None, "nvidia": None, "menu": None, "leave": None, "failsafe": None}
# ------------------------------------------

if getattr(sys, "frozen", False):          # running as a built .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "images")
MEMORY_FILE = os.path.join(BASE_DIR, "locations.json")   # delete to forget locations
IMAGE_NAMES = {
    "ready": "ready.png", "nvidia": "nvidia.png", "menu": "menu.png",
    "leave": "leave.png", "failsafe": "failsafe.png",
}

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.2

# ---------------- shared state ----------------
STATE = {
    "running": False,
    "start": 0.0,
    "end": None,
    "deaths": 0,
    "status": "Idle",
    "kind": "idle",
    "next_check": None,
    "log": [],
}
STOP = threading.Event()


def set_status(text, kind="warn"):
    STATE["status"] = text
    STATE["kind"] = kind


def log(text):
    STATE["log"].append(f"[{time.strftime('%H:%M:%S')}] {text}")
    del STATE["log"][:-200]


def stopped():
    return STOP.is_set()


def sleep_interruptible(seconds):
    end = time.time() + seconds
    while time.time() < end:
        if stopped():
            return False
        time.sleep(0.1)
    return True


def img(key):
    return os.path.join(IMG_DIR, IMAGE_NAMES[key])


def missing_images():
    return [n for n in IMAGE_NAMES.values() if not os.path.exists(os.path.join(IMG_DIR, n))]


# ---------------- remembered locations ----------------
def load_memory():
    try:
        with open(MEMORY_FILE) as f:
            data = json.load(f)
        if data.get("screen") == list(pyautogui.size()):
            return {k: tuple(v) for k, v in data.get("spots", {}).items()}
    except Exception:
        pass
    return {}


def save_memory():
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump({"screen": list(pyautogui.size()),
                       "spots": {k: list(v) for k, v in MEMORY.items()}}, f)
    except Exception:
        pass


MEMORY = load_memory()


def remember(key, box):
    sw, sh = pyautogui.size()
    left = max(0, int(box.left) - REMEMBER_PAD)
    top = max(0, int(box.top) - REMEMBER_PAD)
    right = min(sw, int(box.left + box.width) + REMEMBER_PAD)
    bottom = min(sh, int(box.top + box.height) + REMEMBER_PAD)
    region = (left, top, right - left, bottom - top)
    if MEMORY.get(key) != region:
        first = key not in MEMORY
        MEMORY[key] = region
        save_memory()
        log(f"{'Remembered' if first else 'Updated'} {key} location")


# ---------------- automation ----------------
def locate(key, region):
    try:
        return pyautogui.locateOnScreen(
            img(key), confidence=CONFIDENCE, grayscale=True, region=region)
    except pyautogui.ImageNotFoundException:
        return None


def find(key):
    """Look in the remembered spot first, then fall back to the wider search."""
    spot = MEMORY.get(key)
    if spot:
        box = locate(key, spot)
        if box:
            return pyautogui.center(box)
    box = locate(key, REGIONS[key])
    if box:
        remember(key, box)
        return pyautogui.center(box)
    return None


def click(pos):
    pyautogui.moveTo(pos.x, pos.y, duration=0.2)
    pyautogui.click()


def click_when_found(key, label):
    end = time.time() + STEP_TIMEOUT
    while time.time() < end:
        if stopped():
            return False
        pos = find(key)
        if pos:
            click(pos)
            log(f"Clicked {label}")
            return True
        if not sleep_interruptible(POLL_INTERVAL):
            return False
    log(f"Couldn't find {label}")
    return False


def ready_up():
    """Click Ready if found within READY_TIMEOUT. Returns False only if stopped."""
    set_status("Looking for ready button", "warn")
    end = time.time() + READY_TIMEOUT
    while time.time() < end:
        if stopped():
            return False
        pos = find("ready")
        if pos:
            click(pos)
            log("Readied up")
            return True
        if not sleep_interruptible(READY_RETRY):
            return False
    log("Ready not found, skipping to alive check")
    return True


def wait_until_dead():
    set_status("In match - watching for elimination", "ok")
    while True:
        STATE["next_check"] = time.time() + CHECK_INTERVAL
        if not sleep_interruptible(CHECK_INTERVAL):
            STATE["next_check"] = None
            return False
        STATE["next_check"] = None
        set_status("Scanning screen...", "scan")
        if find("nvidia"):
            STATE["deaths"] += 1
            log(f"Eliminated (death #{STATE['deaths']})")
            return True
        pos = find("failsafe")
        if pos:
            click(pos)
            log("Fail-safe image clicked")
            set_status(f"Fail-safe clicked - checking ready in {FAILSAFE_READY_DELAY}s", "leave")
            if not sleep_interruptible(FAILSAFE_READY_DELAY):
                return False
            ready_pos = find("ready")
            if ready_pos:
                click(ready_pos)
                log("Ready found after fail-safe - clicked")
            else:
                log("Ready not found after fail-safe")
        else:
            log("Still alive")
        set_status("In match - watching for elimination", "ok")


def leave_match():
    set_status("Leaving match", "leave")
    pyautogui.press("esc")
    log("Pressed Esc")
    if not sleep_interruptible(STEP_DELAY):
        return False
    if not click_when_found("menu", "menu"):
        return not stopped()
    if not sleep_interruptible(STEP_DELAY):
        return False
    if not click_when_found("leave", "leave"):
        return not stopped()
    set_status("Back in lobby - waiting", "warn")
    return sleep_interruptible(LOBBY_WAIT)


def worker():
    try:
        set_status(f"Starting in {START_DELAY} seconds - click into Fortnite", "warn")
        if not sleep_interruptible(START_DELAY):
            return
        log("Macro started")
        while not stopped():
            if not ready_up():
                break
            if not wait_until_dead():
                break
            if not leave_match():
                break
    except pyautogui.FailSafeException:
        log("Stopped (mouse in screen corner)")
    except Exception as e:  # keep the window alive and show what went wrong
        log(f"Error: {e}")
    finally:
        STATE["running"] = False
        STATE["next_check"] = None
        STATE["end"] = time.time()
        set_status("Stopped", "stop")
        log("Macro stopped")


# ---------------- window ----------------
# Palette pulled from the logo: amber / gold / cream over deep brown.
BG = "#120b07"
PANEL = "#1d130b"
PANEL2 = "#2a1a0d"
EDGE = "#4d3216"
AMBER = "#e49c24"
GOLD = "#e4b454"
CREAM = "#fce4b4"
DIM = "#a58a62"
KIND_COLORS = {
    "idle": DIM, "ok": "#9be37f", "warn": GOLD,
    "scan": "#7fd3f0", "leave": "#f0a35a", "stop": "#ee6a4f",
}


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rrect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


def fmt_time(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def find_logo():
    for folder in (BASE_DIR, getattr(sys, "_MEIPASS", None)):
        if folder:
            path = os.path.join(folder, "logo.png")
            if os.path.exists(path):
                return path
    return None


def load_logo(size):
    path = find_logo()
    if not path:
        return None
    try:
        from PIL import Image, ImageTk
        resample = getattr(Image, "Resampling", Image).LANCZOS
        im = Image.open(path).convert("RGBA").resize((size, size), resample)
        return ImageTk.PhotoImage(im)
    except Exception:
        return None


class RoundButton(tk.Canvas):
    def __init__(self, parent, text, command, width=206, height=48,
                 bg=AMBER, hover=GOLD, fg="#2a1604"):
        super().__init__(parent, width=width, height=height, bg=BG,
                         highlightthickness=0, bd=0)
        self.cmd, self.w, self.h, self.text = command, width, height, text
        self.colors = (bg, hover, fg)
        self.enabled, self.hovering = True, False
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))
        self.bind("<ButtonRelease-1>", self._click)
        self.draw()

    def draw(self):
        self.delete("all")
        bg, hover, fg = self.colors
        if self.enabled:
            fill = hover if self.hovering else bg
            edge, tcol = mix(fill, "#ffffff", 0.25), fg
        else:
            fill, edge, tcol = PANEL2, EDGE, DIM
        rrect(self, 2, 2, self.w - 2, self.h - 2, 16, fill=fill, outline=edge)
        self.create_text(self.w / 2, self.h / 2, text=self.text, fill=tcol,
                         font=("Segoe UI", 11, "bold"))
        self.config(cursor="hand2" if self.enabled else "arrow")

    def _hover(self, on):
        self.hovering = on
        self.draw()

    def _click(self, _):
        if self.enabled:
            self.cmd()

    def set_enabled(self, on):
        if on != self.enabled:
            self.enabled = on
            self.hovering = False
            self.draw()


class Tile(tk.Canvas):
    def __init__(self, parent, label, color=CREAM, width=204, height=92):
        super().__init__(parent, width=width, height=height, bg=BG,
                         highlightthickness=0, bd=0)
        rrect(self, 2, 2, width - 2, height - 2, 16, fill=PANEL, outline=EDGE)
        self.create_text(18, 22, text=label.upper(), anchor="w", fill=DIM,
                         font=("Segoe UI", 8, "bold"))
        self.create_line(18, 36, 44, 36, fill=AMBER, width=2)
        self.val = self.create_text(18, 62, text="--", anchor="w", fill=color,
                                    font=("Consolas", 22, "bold"))

    def set(self, text, color=None):
        self.itemconfig(self.val, text=text)
        if color:
            self.itemconfig(self.val, fill=color)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pirate Shop Macro")
        self.geometry("460x690")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.shown_log = 0
        self.logo = load_logo(104)
        self.icon = load_logo(64)
        if self.icon:
            self.iconphoto(True, self.icon)
        self._dark_titlebar()

        # ---- header: glowing logo + title ----
        head = tk.Canvas(self, width=460, height=124, bg=BG, highlightthickness=0)
        head.pack(pady=(10, 0))
        cx, cy = 74, 62
        for r in range(58, 14, -3):
            t = ((58 - r) / 44) ** 1.5 * 0.5
            head.create_oval(cx - r, cy - r, cx + r, cy + r,
                             fill=mix(BG, AMBER, t), outline="")
        if self.logo:
            head.create_image(cx, cy, image=self.logo)
        head.create_text(142, 46, text="PIRATE SHOP", anchor="w", fill=GOLD,
                         font=("Segoe UI", 22, "bold"))
        head.create_text(142, 76, text="MACRO", anchor="w", fill=CREAM,
                         font=("Segoe UI", 22, "bold"))
        head.create_text(144, 104, text="auto-ready  \u2022  auto-lobby", anchor="w",
                         fill=DIM, font=("Segoe UI", 9))

        # ---- gold divider ----
        div = tk.Canvas(self, width=424, height=4, bg=BG, highlightthickness=0)
        div.pack(pady=(4, 10))
        for x in range(0, 424, 2):
            div.create_line(x, 1, x, 3, fill=mix(BG, AMBER, 1 - abs(x - 212) / 212),
                            width=2)

        # ---- status pill ----
        self.pill = tk.Canvas(self, width=424, height=50, bg=BG, highlightthickness=0)
        self.pill.pack()
        rrect(self.pill, 2, 2, 422, 48, 18, fill=PANEL, outline=EDGE)
        self.dot = self.pill.create_oval(20, 19, 32, 31, fill=DIM, outline="")
        self.status_txt = self.pill.create_text(46, 25, text="Idle", anchor="w",
                                                fill=DIM, font=("Segoe UI", 11, "bold"))

        # ---- stat tiles ----
        grid = tk.Frame(self, bg=BG)
        grid.pack(pady=(12, 0))
        self.tiles = {
            "time": Tile(grid, "Run time", CREAM),
            "deaths": Tile(grid, "Deaths", "#ee6a4f"),
            "avg": Tile(grid, "Avg / death", GOLD),
            "next": Tile(grid, "Next check", AMBER),
        }
        self.tiles["time"].grid(row=0, column=0, padx=(0, 8), pady=(0, 8))
        self.tiles["deaths"].grid(row=0, column=1, padx=(8, 0), pady=(0, 8))
        self.tiles["avg"].grid(row=1, column=0, padx=(0, 8))
        self.tiles["next"].grid(row=1, column=1, padx=(8, 0))

        # ---- buttons ----
        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=(16, 4))
        self.start_btn = RoundButton(btns, "\u25B6  START", self.start)
        self.start_btn.grid(row=0, column=0, padx=(0, 8))
        self.stop_btn = RoundButton(btns, f"\u25A0  STOP  ({STOP_KEY.upper()})", self.stop,
                                    bg="#a8402a", hover="#c9573b", fg=CREAM)
        self.stop_btn.grid(row=0, column=1, padx=(8, 0))

        self.top_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text="Always on top", variable=self.top_var,
                       command=lambda: self.attributes("-topmost", self.top_var.get()),
                       fg=DIM, bg=BG, selectcolor=PANEL, activebackground=BG,
                       activeforeground=CREAM, bd=0, highlightthickness=0,
                       font=("Segoe UI", 9)).pack(pady=(2, 6))

        # ---- activity log ----
        tk.Label(self, text="RECENT ACTIVITY", fg=AMBER, bg=BG,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=22)
        frame = tk.Frame(self, bg="#0d0805", highlightthickness=1,
                         highlightbackground=EDGE)
        frame.pack(fill="x", padx=20, pady=(3, 6))
        self.log_box = tk.Text(frame, height=7, bg="#0d0805", fg=DIM, relief="flat",
                               font=("Consolas", 9), state="disabled", wrap="none",
                               padx=10, pady=8, highlightthickness=0, bd=0)
        self.log_box.pack(fill="x")
        self.log_box.tag_config("ts", foreground="#6f5c3e")
        self.log_box.tag_config("info", foreground="#d9c39a")
        self.log_box.tag_config("good", foreground="#9be37f")
        self.log_box.tag_config("bad", foreground="#ee6a4f")

        tk.Label(self, text=f"{STOP_KEY.upper()} stops from anywhere  \u2022  "
                            "mouse into a corner = emergency stop",
                 fg="#6f5c3e", bg=BG, font=("Segoe UI", 8)).pack()

        try:
            keyboard.add_hotkey(STOP_KEY, self.stop)
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh()

    def _dark_titlebar(self):
        try:
            self.update()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(ctypes.c_int(1)), 4)
        except Exception:
            pass

    def start(self):
        if STATE["running"]:
            return
        missing = missing_images()
        if missing:
            messagebox.showerror(
                "Missing images",
                f"Put these in:\n{IMG_DIR}\n\n" + "\n".join(missing))
            return
        STATE.update(running=True, start=time.time(), end=None, deaths=0, next_check=None)
        STATE["log"].clear()
        self.shown_log = 0
        STOP.clear()
        threading.Thread(target=worker, daemon=True).start()

    def stop(self):
        STOP.set()

    def on_close(self):
        STOP.set()
        self.destroy()

    @staticmethod
    def _tag_for(msg):
        low = msg.lower()
        if any(w in low for w in ("eliminated", "error", "couldn't", "not found", "stopped")):
            return "bad"
        if any(w in low for w in ("clicked", "readied", "remembered", "updated", "started")):
            return "good"
        return "info"

    def refresh(self):
        now = time.time()
        running = STATE["running"]
        elapsed = ((STATE["end"] or now) - STATE["start"]) if STATE["start"] else 0
        deaths = STATE["deaths"]

        color = KIND_COLORS[STATE["kind"]]
        pulse = running and int(now * 2) % 2 == 0
        self.pill.itemconfig(self.dot, fill=mix(color, PANEL, 0.55) if pulse else color)
        text = STATE["status"]
        self.pill.itemconfig(self.status_txt, text=text if len(text) < 47 else text[:44] + "...",
                             fill=color)

        self.tiles["time"].set(fmt_time(elapsed))
        self.tiles["deaths"].set(str(deaths))
        self.tiles["avg"].set(fmt_time(elapsed / deaths) if deaths else "--:--:--")
        nc = STATE["next_check"]
        self.tiles["next"].set(f"{max(0, math.ceil(nc - now))}s" if nc else "--")

        self.start_btn.set_enabled(not running)
        self.stop_btn.set_enabled(running)

        lines = STATE["log"]
        if self.shown_log > len(lines):
            self.shown_log = 0
        if self.shown_log < len(lines):
            self.log_box.config(state="normal")
            if self.shown_log == 0:
                self.log_box.delete("1.0", "end")
            for line in lines[self.shown_log:]:
                ts, _, msg = line.partition("] ")
                self.log_box.insert("end", ts + "]  ", "ts")
                self.log_box.insert("end", msg + "\n", self._tag_for(msg))
            self.log_box.see("end")
            self.log_box.config(state="disabled")
            self.shown_log = len(lines)

        self.after(250, self.refresh)


if __name__ == "__main__":
    App().mainloop()
