"""
Pomodoro Timer — pure tkinter GUI + floating overlay + system tray + sound.
No HTML, no pywebview. Overlay is a child of the main timer.
"""
import threading
import time
import os
import sys
import struct
import math
import tempfile
import json
import wave
import traceback
from datetime import datetime

# ─── Logging ────────────────────────────────────────────────────────
_LOG_FILE = os.path.join(os.path.expanduser("~"), "pomodoro_log.txt")

def _log(msg):
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except:
        pass

def _log_error(msg):
    _log(f"ERROR: {msg}")
    _log(traceback.format_exc())

# ─── Sound synthesis ──────────────────────────────────────────────

def _write_wav(filepath, frames, sr=44100):
    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(bytes(frames))

def _gen_ding(fp):
    sr=44100; gap=int(sr*0.12); da=int(sr*0.18); db=int(sr*0.28); total=da+gap+db
    frames=bytearray()
    for i in range(total):
        t=i/sr; sample=0.0
        if i<da:
            env=max(0.0,1.0-(i/da)**0.6)
            s=0.5*math.sin(2*math.pi*880*t)+0.3*math.sin(2*math.pi*880*2*t)+0.15*math.sin(2*math.pi*880*3*t)+0.08*math.sin(2*math.pi*880*5*t)
            sample=s*env
        elif i>=da+gap and i<total:
            j=i-da-gap; env=max(0.0,1.0-(j/db)**0.5)
            s=0.5*math.sin(2*math.pi*1100*t)+0.3*math.sin(2*math.pi*1100*2*t)+0.15*math.sin(2*math.pi*1100*3*t)+0.08*math.sin(2*math.pi*1100*5*t)
            sample=s*env
        pcm=max(-32768,min(32767,int(sample*0.7*32767)))
        frames.extend(struct.pack('<h',pcm))
    _write_wav(fp,frames)

def _gen_break(fp):
    sr=44100; notes=[784,1047,1319,1568]; nd=int(sr*0.15); gap=int(sr*0.08); total=len(notes)*(nd+gap)
    frames=bytearray()
    for i in range(total):
        ni=i//(nd+gap)
        if ni>=len(notes): break
        j=i%(nd+gap)
        if j>=nd: frames.extend(struct.pack('<h',0)); continue
        f=notes[ni]; t=i/sr; env=max(0.0,1.0-(j/nd)**0.5)
        s=0.5*math.sin(2*math.pi*f*t)+0.3*math.sin(2*math.pi*f*2*t)+0.15*math.sin(2*math.pi*f*3*t)+0.08*math.sin(2*math.pi*f*5*t)
        pcm=max(-32768,min(32767,int(s*env*0.65*32767)))
        frames.extend(struct.pack('<h',pcm))
    _write_wav(fp,frames)

def _gen_done(fp):
    sr=44100; notes=[(523,0.12),(659,0.12),(784,0.12),(1047,0.15),(1319,0.35)]
    gap=int(sr*0.035); total=sum(int(sr*d)+gap for _,d in notes)
    frames=bytearray()
    for i in range(total):
        el=0; sample=0.0
        for f,d in notes:
            ns=int(sr*d)
            if el<=i<el+ns:
                j=i-el; t=i/sr; env=max(0.0,1.0-(j/ns)**0.5)
                s=0.4*math.sin(2*math.pi*f*t)+0.22*math.sin(2*math.pi*f*2*t)+0.12*math.sin(2*math.pi*f*3*t)+0.07*math.sin(2*math.pi*f*4*t)+0.04*math.sin(2*math.pi*f*6*t)+0.03*math.sin(2*math.pi*f*8*t)
                sample=s*env*0.65; break
            el+=ns+gap
        pcm=max(-32768,min(32767,int(sample*32767)))
        frames.extend(struct.pack('<h',pcm))
    _write_wav(fp,frames)

def _gen_start(fp):
    sr=44100; notes=[(659,0.1),(784,0.1),(1047,0.12),(1319,0.18)]
    gap=int(sr*0.025); total=sum(int(sr*d)+gap for _,d in notes)
    frames=bytearray()
    for i in range(total):
        el=0; sample=0.0
        for f,d in notes:
            ns=int(sr*d)
            if el<=i<el+ns:
                j=i-el; t=i/sr; env=max(0.0,1.0-(j/ns)**0.5)
                s=0.45*math.sin(2*math.pi*f*t)+0.25*math.sin(2*math.pi*f*2*t)+0.12*math.sin(2*math.pi*f*3*t)+0.06*math.sin(2*math.pi*f*4*t)+0.04*math.sin(2*math.pi*f*6*t)
                sample=s*env*0.6; break
            el+=ns+gap
        pcm=max(-32768,min(32767,int(sample*32767)))
        frames.extend(struct.pack('<h',pcm))
    _write_wav(fp,frames)

# Cache sounds
_CHIME_DIR=os.path.join(tempfile.gettempdir(),"pomodoro_chimes")
os.makedirs(_CHIME_DIR,exist_ok=True)
DONE_CHIME =os.path.join(_CHIME_DIR,"done_chime.wav")
BREAK_CHIME=os.path.join(_CHIME_DIR,"break_chime.wav")
START_CHIME=os.path.join(_CHIME_DIR,"start_chime.wav")
TICK_CHIME =os.path.join(_CHIME_DIR,"tick_chime.wav")
if not os.path.exists(DONE_CHIME):  _gen_done(DONE_CHIME)
if not os.path.exists(BREAK_CHIME): _gen_break(BREAK_CHIME)
if not os.path.exists(START_CHIME): _gen_start(START_CHIME)
if not os.path.exists(TICK_CHIME):  _gen_ding(TICK_CHIME)

def _play_async(wav):
    try:
        import winsound
        winsound.PlaySound(wav,winsound.SND_FILENAME|winsound.SND_ASYNC)
    except: pass

def _notify(title,msg):
    try:
        from plyer import notification
        notification.notify(title=title,message=msg,app_name="Pomodoro",timeout=8)
    except: pass

# ─── Pomodoro Timer App ────────────────────────────────────────────

class PomodoroApp:
    def __init__(self):
        try:
            _log("=== Pomodoro Timer Starting ===")
            _log(f"Frozen: {getattr(sys, 'frozen', False)}")
            if getattr(sys, 'frozen', False):
                _log(f"_MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")

            import tkinter as tk
            from PIL import Image, ImageTk

            self.root = tk.Tk()
            self.root.title("Pomodoro Timer")
            self.root.geometry("370x480")
            self.root.resizable(False, False)
            self.root.configure(bg="#a8d8ea")
            _log("Main window created")

            # Background image — stored here, drawn on canvas in _build_ui
            self._bg_photo = None
            self._bg_pil   = None
            self._pulse_val = 0.0
            self._pulse_dir = 1
            self._pulse_id  = None
            self._pill_hovered = None
            self._settings_visible = False
            self._settings_anim_y  = -300
            self._settings_anim_id = None
            try:
                if getattr(sys, 'frozen', False):
                    _bg_base = sys._MEIPASS
                else:
                    _bg_base = os.path.dirname(os.path.abspath(__file__))
                _bg_path = os.path.join(_bg_base, "background.png")
                if os.path.exists(_bg_path):
                    _bg_img = Image.open(_bg_path).resize((370, 480), Image.LANCZOS)
                    self._bg_pil   = _bg_img          # raw PIL — composited in _build_ui
                    self._bg_photo = ImageTk.PhotoImage(_bg_img)
                    _log("Background image loaded")
                else:
                    _log("Background.png not found")
            except Exception as e:
                _log_error(f"Background load failed: {e}")

            # State
            self.durations = {"pomodoro": 25, "shortBreak": 5, "longBreak": 15}
            self.goal = 4
            self.mode = "pomodoro"
            self.time_left = 25 * 60
            self.total_time = self.time_left
            self.running = False
            self.completed = 0
            self.timer_id = None
            self.overlay_visible = False

            self.COLORS = {"pomodoro": "#e04545", "shortBreak": "#18a84a", "longBreak": "#2b7fd4"}
            self.LABELS = {"pomodoro": "Pomodoro Session", "shortBreak": "Short Break", "longBreak": "Long Break"}
            self.OVERLAY_LABELS = {"pomodoro": "Work", "shortBreak": "Short", "longBreak": "Long"}

            # UI
            self._build_ui()
            self._update_display()
            self._update_progress()
            self._update_color()
            _log("UI built")

            # System tray
            self._tray_icon = None
            self._start_tray()

            # Handle close
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

            # Set taskbar icon
            self._set_taskbar_icon()
            _log("Init complete")
        except Exception as e:
            _log_error(f"Init failed: {e}")
            raise

    def _set_taskbar_icon(self):
        try:
            import ctypes
            # Set explicit app ID so Windows uses our icon for taskbar
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PomodoroTimer.CY0214.2.0")
            if getattr(sys, 'frozen', False):
                # Use the embedded icon from the exe itself
                self.root.iconbitmap(default=sys.executable)
            else:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cinnamoroll_icon.ico")
                if os.path.exists(icon_path):
                    self.root.iconbitmap(default=icon_path)
        except Exception as e:
            _log_error(f"Icon load failed: {e}")


    # ─── Colour helpers ────────────────────────────────────────────────
    def _hex_rgb(self, h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_hex(self, r, g, b):
        return f'#{int(max(0,min(255,r))):02x}{int(max(0,min(255,g))):02x}{int(max(0,min(255,b))):02x}'

    def _darken(self, col, f=0.82):
        r, g, b = self._hex_rgb(col)
        return self._rgb_hex(r*f, g*f, b*f)

    def _lighten(self, col, f=1.28):
        r, g, b = self._hex_rgb(col)
        return self._rgb_hex(r*f, g*f, b*f)

    def _blend(self, c1, c2, t):
        r1,g1,b1 = self._hex_rgb(c1); r2,g2,b2 = self._hex_rgb(c2)
        return self._rgb_hex(r1+(r2-r1)*t, g1+(g2-g1)*t, b1+(b2-b1)*t)

    # ─── Pill-button helpers (feature 2) ───────────────────────────────
    def _pill_hover(self, mode, entering):
        self._pill_hovered = mode if entering else None
        self._redraw_pill(mode)

    def _redraw_pill(self, mode):
        c = self.mode_buttons.get(mode)
        if c is None:
            return
        w = int(c['width']); h = int(c['height']); r = h // 2
        c.delete("all")
        is_active  = (mode == self.mode)
        is_hovered = (self._pill_hovered == mode)
        lbl = {"pomodoro": "Pomodoro", "shortBreak": "Short Break",
               "longBreak": "Long Break"}[mode]
        if is_active:
            fill = self._lighten(self.COLORS[mode], 1.08) if is_hovered else self.COLORS[mode]
            tc, fw, oc = "white", "bold", fill
        else:
            fill = "#c0dff0" if is_hovered else getattr(self, '_CARD', "#edf7fc")
            tc, fw, oc = "#2c3e50", "normal", "#7db5cc"
        # Left arc
        c.create_arc(0, 1, 2*r, h-1, start=90, extent=180, fill=fill, outline=oc, width=1)
        # Right arc
        c.create_arc(w-2*r, 1, w, h-1, start=270, extent=180, fill=fill, outline=oc, width=1)
        # Middle rect
        c.create_rectangle(r, 1, w-r, h-1, fill=fill, outline=fill)
        if not is_active:
            c.create_line(r, 1, w-r, 1, fill=oc); c.create_line(r, h-1, w-r, h-1, fill=oc)
        c.create_text(w//2, h//2+1, text=lbl, font=("Segoe UI", 9, fw), fill=tc)

    # ─── Button hover helper (feature 5) ───────────────────────────────
    def _add_hover(self, btn, base_color):
        dark = self._darken(base_color, 0.82)
        btn.bind("<Enter>", lambda e: btn.config(bg=dark))
        btn.bind("<Leave>", lambda e: btn.config(bg=base_color))

    # ─── Pulse animation (feature 6) ───────────────────────────────────
    def _start_pulse(self):
        self._stop_pulse()
        self._pulse_val = 0.0; self._pulse_dir = 1
        self._do_pulse()

    def _stop_pulse(self):
        if self._pulse_id:
            try: self.root.after_cancel(self._pulse_id)
            except: pass
            self._pulse_id = None
        self._pulse_val = 0.0

    def _do_pulse(self):
        if not self.running:
            self._pulse_val = 0.0; return
        self._pulse_val += 0.045 * self._pulse_dir
        if   self._pulse_val >= 1.0: self._pulse_val = 1.0; self._pulse_dir = -1
        elif self._pulse_val <= 0.0: self._pulse_val = 0.0; self._pulse_dir =  1
        self._update_progress()
        self._pulse_id = self.root.after(50, self._do_pulse)

    # ─── Settings slide animation (feature 10) ─────────────────────────
    def _slide_in_settings(self):
        self._settings_visible = True
        self._settings_anim_y = -300
        self._settings_shadow.place(x=13, y=-296, width=350, height=10)
        self._settings_shadow.lift()
        self.settings_frame.place(x=10, y=self._settings_anim_y, width=350)
        self.settings_frame.lift()
        self._animate_slide(target=42, speed=26)

    def _slide_out_settings(self):
        self._settings_visible = False
        self._animate_slide(target=-300, speed=28,
                            on_done=lambda: (
                                self.settings_frame.place_forget(),
                                self._settings_shadow.place_forget()))

    def _animate_slide(self, target, speed, on_done=None):
        if self._settings_anim_id:
            try: self.root.after_cancel(self._settings_anim_id)
            except: pass
            self._settings_anim_id = None
        def step():
            cur = self._settings_anim_y
            new = cur + speed if target > cur else cur - speed
            new = max(min(new, max(cur, target)), min(cur, target))
            self._settings_anim_y = new
            try:
                self.settings_frame.place(x=10, y=new, width=350)
                sh = max(self.settings_frame.winfo_reqheight(), 20)
                self._settings_shadow.place(x=13, y=new+4, width=350, height=sh)
                self._settings_shadow.lower(self.settings_frame)
            except: return
            if new != target:
                self._settings_anim_id = self.root.after(14, step)
            else:
                self._settings_anim_id = None
                if on_done: on_done()
        step()

    def _build_ui(self):
        import tkinter as tk
        from PIL import Image, ImageDraw, ImageTk

        W, H   = 370, 480
        CARD   = "#edf7fc"
        SBG    = "#ddeef7"
        SFG    = "#2c3e50"
        SBTN   = "#b8d4e3"
        CX1, CY1, CX2, CY2 = 45, 50, 325, 445
        R      = 14          # corner radius
        self._CARD = CARD

        # ── Bake rounded card into background (feature 1) ─────────────
        base = (self._bg_pil.copy().convert("RGBA") if self._bg_pil is not None
                else Image.new("RGBA", (W, H), (168, 216, 234, 255)))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)
        # Shadow
        dr.rounded_rectangle([CX1+4, CY1+4, CX2+4, CY2+4], radius=R,
                              fill=(80, 140, 175, 90))
        # Card face
        dr.rounded_rectangle([CX1, CY1, CX2, CY2], radius=R,
                              fill=(237, 247, 252, 252),
                              outline=(180, 220, 235, 200), width=1)
        self._bg_photo = ImageTk.PhotoImage(Image.alpha_composite(base, ov).convert("RGB"))

        # ── Root canvas ───────────────────────────────────────────────
        rc = tk.Canvas(self.root, width=W, height=H, highlightthickness=0, bd=0)
        rc.pack(fill="both", expand=True)
        self._rc = rc
        rc.create_image(0, 0, anchor="nw", image=self._bg_photo)

        # Gear icon — no bg box (drawn directly on canvas)
        rc.create_text(28, 28, text="⚙", font=("Segoe UI", 14),
                       fill="#3a4d5c", anchor="center", tags="gear")
        rc.tag_bind("gear", "<Button-1>", self._toggle_settings)
        rc.tag_bind("gear", "<Enter>",
                    lambda e: rc.itemconfig("gear", fill="#1a2a3a"))
        rc.tag_bind("gear", "<Leave>",
                    lambda e: rc.itemconfig("gear", fill="#3a4d5c"))

        # ── Settings panel (slide-in overlay) ─────────────────────────
        # Shadow backing — shown behind settings_frame during slide
        self._settings_shadow = tk.Frame(self.root, bg="#7aaec8",
                                         bd=0, highlightthickness=0)
        self.settings_frame = tk.Frame(self.root, bg=SBG, bd=0,
                                       highlightthickness=2,
                                       highlightbackground="#5a9ebd")
        tk.Label(self.settings_frame, text="⏱ Durations (min)",
                 font=("Segoe UI", 10, "bold"), bg=SBG, fg=SFG
                 ).pack(anchor="w", pady=(8, 6), padx=10)
        self.s_vars = {}
        for key, lbl, default in [("pomodoro", "Pomodoro:", 25),
                                   ("shortBreak", "Short Break:", 5),
                                   ("longBreak", "Long Break:", 15)]:
            row = tk.Frame(self.settings_frame, bg=SBG)
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=lbl, font=("Segoe UI", 9), bg=SBG,
                     fg="#3d5060", width=14, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(default))
            tk.Entry(row, textvariable=var, width=6, font=("Segoe UI", 9),
                     bg=SBTN, fg=SFG, insertbackground=SFG,
                     relief="flat", justify="center").pack(side="left")
            self.s_vars[key] = var
        row = tk.Frame(self.settings_frame, bg=SBG)
        row.pack(fill="x", padx=10, pady=2)
        tk.Label(row, text="Cycles:", font=("Segoe UI", 9), bg=SBG,
                 fg="#3d5060", width=14, anchor="w").pack(side="left")
        self.s_cycle_var = tk.StringVar(value="4")
        tk.Entry(row, textvariable=self.s_cycle_var, width=6,
                 font=("Segoe UI", 9), bg=SBTN, fg=SFG,
                 insertbackground=SFG, relief="flat",
                 justify="center").pack(side="left")
        self.s_vars["cycle"] = self.s_cycle_var
        overlay_row = tk.Frame(self.settings_frame, bg=SBG)
        overlay_row.pack(fill="x", padx=10, pady=(10, 2))
        self.overlay_toggle_btn = tk.Button(
            overlay_row, text="Show Overlay",
            font=("Segoe UI", 9, "bold"), bg="#3498db", fg="white",
            relief="flat", cursor="hand2", command=self._toggle_overlay)
        self.overlay_toggle_btn.pack(fill="x")
        tk.Button(self.settings_frame, text="Apply",
                  font=("Segoe UI", 9, "bold"), bg="#3498db", fg="white",
                  relief="flat", cursor="hand2",
                  command=self._apply_settings
                  ).pack(fill="x", padx=10, pady=(8, 8))
        self.s_err = tk.Label(self.settings_frame,
                              text="Durations: 1-120, Cycles: 1-20",
                              font=("Segoe UI", 8), bg=SBG, fg="#ff6b6b")
        self.s_err.pack_forget()

        # ── Card frame — mode-coloured highlight border (feature 4) ───
        self._card_frame = tk.Frame(self.root, bg=CARD, bd=0,
                                    highlightthickness=2,
                                    highlightbackground="#e04545")
        self._card_frame.place(x=CX1, y=CY1, width=CX2-CX1, height=CY2-CY1)
        card = self._card_frame

        # ── Title ──────────────────────────────────────────────────────
        self.title_label = tk.Label(card, text="🍅 Pomodoro Timer",
                                    font=("Segoe UI", 16, "bold"),
                                    bg=CARD, fg="#ff6b6b")
        self.title_label.pack(pady=(14, 6))

        # ── Pill-shaped mode buttons (feature 2) ───────────────────────
        mode_frame = tk.Frame(card, bg=CARD)
        mode_frame.pack(pady=(0, 10))
        self.mode_buttons = {}
        pill_w = {"pomodoro": 80, "shortBreak": 90, "longBreak": 86}
        for mode in ["pomodoro", "shortBreak", "longBreak"]:
            bw, bh = pill_w[mode], 26
            c = tk.Canvas(mode_frame, width=bw, height=bh,
                          highlightthickness=0, bd=0, cursor="hand2", bg=CARD)
            c.pack(side="left", padx=3)
            self.mode_buttons[mode] = c
            c.bind("<Button-1>", lambda e, m=mode: self._set_mode(m))
            c.bind("<Enter>",    lambda e, m=mode: self._pill_hover(m, True))
            c.bind("<Leave>",    lambda e, m=mode: self._pill_hover(m, False))

        # ── Progress ring canvas ───────────────────────────────────────
        self.canvas = tk.Canvas(card, width=180, height=180,
                                bg=CARD, highlightthickness=0)
        self.canvas.pack(pady=(0, 5))
        self.timer_text = tk.Label(self.canvas, text="25:00",
                                   font=("Consolas", 28, "bold"),
                                   bg=CARD, fg="#ff6b6b")
        self.timer_text.place(relx=0.5, rely=0.5, anchor="center")

        # ── Buttons with hover (feature 5) ────────────────────────────
        ctrl_frame = tk.Frame(card, bg=CARD)
        ctrl_frame.pack(pady=(8, 5))

        self.reset_btn = tk.Button(ctrl_frame, text="Reset",
                                   font=("Segoe UI", 12, "bold"),
                                   bg="#ff6b6b", fg="white", relief="flat",
                                   cursor="hand2", width=10, command=self._reset)
        self.reset_btn.pack(side="left", padx=5)
        self._add_hover(self.reset_btn, "#ff6b6b")

        self.start_btn = tk.Button(ctrl_frame, text="Start",
                                   font=("Segoe UI", 12, "bold"),
                                   bg="#3498db", fg="white", relief="flat",
                                   cursor="hand2", width=10, command=self._start)
        self.start_btn.pack(side="left", padx=5)
        self._add_hover(self.start_btn, "#3498db")

        self.pause_btn = tk.Button(ctrl_frame, text="Pause",
                                   font=("Segoe UI", 12, "bold"),
                                   bg="#f39c12", fg="white", relief="flat",
                                   cursor="hand2", width=10, command=self._pause)
        self.pause_btn.pack_forget()
        self._add_hover(self.pause_btn, "#f39c12")

        # ── Session info ───────────────────────────────────────────────
        self.session_label = tk.Label(card, text="Pomodoro Session",
                                      font=("Segoe UI", 10),
                                      bg=CARD, fg="#374f62")
        self.session_label.pack(pady=(5, 2))
        self.completed_label = tk.Label(card, text="Completed: 0 sessions 🍅",
                                        font=("Segoe UI", 9),
                                        bg=CARD, fg="#374f62")
        self.completed_label.pack()

        # Draw initial pills
        self._update_mode_buttons()

        # Click outside to close settings
        self.root.bind("<Button-1>", self._on_click_outside)

    def _on_click_outside(self, event):
        if getattr(self, '_settings_visible', False) and self.settings_frame.winfo_viewable():
            if not self._is_child_of(event.widget, self.settings_frame):
                try:
                    rx = event.x_root - self.root.winfo_rootx()
                    ry = event.y_root - self.root.winfo_rooty()
                    if abs(rx - 28) < 16 and abs(ry - 28) < 16:
                        return
                except Exception:
                    pass
                self._close_settings()

    def _is_child_of(self, widget, parent):
        while widget:
            if widget == parent:
                return True
            try:
                widget = widget.master
            except:
                break
        return False

    def _toggle_settings(self, event=None):
        if getattr(self, '_settings_visible', False):
            self._close_settings()
        else:
            self._slide_in_settings()

    def _close_settings(self):
        self.s_err.pack_forget()
        self._slide_out_settings()

    def _apply_settings(self):
        try:
            p = int(self.s_vars["pomodoro"].get())
            s = int(self.s_vars["shortBreak"].get())
            l = int(self.s_vars["longBreak"].get())
            c = int(self.s_vars["cycle"].get())
            if not (1 <= p <= 120 and 1 <= s <= 120 and 1 <= l <= 120 and 1 <= c <= 20):
                self.s_err.pack()
                return
            self.durations = {"pomodoro": p, "shortBreak": s, "longBreak": l}
            self.goal = c
            self.s_err.pack_forget()
            self._close_settings()
            self._reset()
        except ValueError:
            self.s_err.pack()

    def _toggle_overlay(self):
        if self.overlay_visible:
            self._overlay_hide_safe()
        else:
            self._show_overlay()

    def _show_overlay(self):
        if self.overlay_visible:
            return
        _log("Showing overlay...")
        self.overlay_visible = True
        self.overlay_toggle_btn.config(text="Hide Overlay")

        # If overlay window already exists, just show it
        if hasattr(self, 'overlay_win') and self.overlay_win is not None:
            try:
                if self.overlay_win.winfo_exists():
                    self.overlay_win.deiconify()
                    self.overlay_win.attributes("-topmost", True)
                    # Restart the update loop
                    try:
                        self._update_overlay()
                    except:
                        pass
                    return
            except:
                pass

        def create_overlay():
            try:
                import tkinter as tk
                self.overlay_win = tk.Tk()
                self.overlay_win.title("")
                self.overlay_win.overrideredirect(True)
                self.overlay_win.attributes("-topmost", True)
                self.overlay_win.configure(bg="#1a1a2e")
                self.overlay_win.resizable(False, False)
                self.overlay_win.update_idletasks()

                sw = self.overlay_win.winfo_screenwidth()
                sh = self.overlay_win.winfo_screenheight()
                self.overlay_win.geometry(f"75x45+{sw-75}+{sh-78}")

                top_frame = tk.Frame(self.overlay_win, bg="#1a1a2e")
                top_frame.pack(fill="x", padx=3, pady=(2, 0))
                self.overlay_session = tk.Label(top_frame, text="Work", font=("Segoe UI", 8, "bold"), bg="#1a1a2e", fg="#ff6b6b")
                self.overlay_session.pack(expand=True)
                self.overlay_time = tk.Label(self.overlay_win, text="25:00", font=("Consolas", 14, "bold"), bg="#1a1a2e", fg="#ff6b6b")
                self.overlay_time.pack(pady=(0, 2))

                drag = {"x": 0, "y": 0}
                def start_drag(e):
                    drag["x"] = e.x; drag["y"] = e.y
                def do_drag(e):
                    self.overlay_win.geometry(f"+{self.overlay_win.winfo_x()+e.x-drag['x']}+{self.overlay_win.winfo_y()+e.y-drag['y']}")
                for w in [self.overlay_win, self.overlay_session, self.overlay_time]:
                    w.bind("<Button-1>", start_drag)
                    w.bind("<B1-Motion>", do_drag)

                # Local menu commands
                def overlay_show_timer():
                    self.root.after(0, lambda: (self.root.deiconify(), self.root.lift()))
                def overlay_start():
                    self.root.after(0, self._start)
                def overlay_pause():
                    self.root.after(0, self._pause)
                def overlay_reset():
                    self.root.after(0, self._reset)
                def overlay_hide():
                    self.overlay_win.after(0, self._hide_overlay)
                def overlay_quit():
                    self.overlay_win.after(0, self.overlay_win.destroy)
                    self.root.after(0, lambda: self._on_close(from_tray=True))
                def overlay_popup(event):
                    self.overlay_menu.tk_popup(event.x_root, event.y_root)
                    self.overlay_menu.grab_release()

                self.overlay_menu = tk.Menu(self.overlay_win, tearoff=0, bg="#1a1a2e", fg="#ffffff",
                                             activebackground="#ff6b6b", activeforeground="#ffffff")
                self.overlay_menu.add_command(label="Show Timer", command=overlay_show_timer)
                self.overlay_menu.add_separator()
                self.overlay_menu.add_command(label="Start", command=overlay_start)
                self.overlay_menu.add_command(label="Pause", command=overlay_pause)
                self.overlay_menu.add_command(label="Reset", command=overlay_reset)
                self.overlay_menu.add_separator()
                self.overlay_menu.add_command(label="Hide Overlay", command=overlay_hide)
                self.overlay_menu.add_separator()
                self.overlay_menu.add_command(label="Quit", command=overlay_quit)

                for w in [self.overlay_win, self.overlay_session, self.overlay_time]:
                    w.bind("<Button-3>", overlay_popup)

                _log("Overlay entering mainloop")
                self._update_overlay()
                self.overlay_win.mainloop()
                _log("Overlay mainloop ended")
            except Exception as e:
                _log_error(f"Overlay creation failed: {e}")

        self._overlay_thread = threading.Thread(target=create_overlay, daemon=True)
        self._overlay_thread.start()
        _log("Overlay thread started")

    def _overlay_hide_safe(self):
        try:
            if hasattr(self, 'overlay_win') and self.overlay_win is not None:
                self.overlay_win.after(0, self._hide_overlay)
        except:
            pass

    def _hide_overlay(self):
        try:
            if hasattr(self, 'overlay_win') and self.overlay_win is not None:
                if self.overlay_win.winfo_exists():
                    self.overlay_win.withdraw()
            self.overlay_visible = False
            if hasattr(self, 'overlay_toggle_btn'):
                self.overlay_toggle_btn.config(text="Show Overlay")
        except:
            pass

    def _update_overlay(self):
        if not self.overlay_visible or not hasattr(self, 'overlay_win'):
            return
        try:
            if hasattr(self.overlay_win, 'winfo_exists') and not self.overlay_win.winfo_exists():
                return
            m = self.time_left // 60
            s = self.time_left % 60
            self.overlay_time.config(text=f"{m:02d}:{s:02d}")
            c = self.COLORS[self.mode]
            label = self.OVERLAY_LABELS[self.mode]
            self.overlay_session.config(text=label, fg=c)
            self.overlay_time.config(fg=c)
        except:
            pass
        if self.overlay_visible:
            try:
                self._overlay_after_id = self.overlay_win.after(1000, self._update_overlay)
            except:
                pass

    def _set_mode(self, mode):
        if self.running:
            return
        self.mode = mode
        self._reset()
        self._update_mode_buttons()
        self._update_color()
        self._update_label()

    def _update_mode_buttons(self):
        for mode in self.mode_buttons:
            self._redraw_pill(mode)

    def _start(self):
        self.running = True
        self.start_btn.pack_forget()
        self.pause_btn.pack(side="left", padx=5)
        _play_async(START_CHIME)
        self._start_pulse()
        self._tick()

    def _pause(self):
        self.running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self._stop_pulse()
        self._update_progress()
        self.start_btn.pack(side="left", padx=5)
        self.pause_btn.pack_forget()

    def _reset(self):
        self.running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self._stop_pulse()
        self.time_left = self.durations[self.mode] * 60
        self.total_time = self.time_left
        self._update_display()
        self._update_progress()
        self._update_color()
        self._update_label()
        self._update_mode_buttons()
        self.start_btn.pack(side="left", padx=5)
        self.pause_btn.pack_forget()

    def _tick(self):
        if not self.running:
            return
        self.time_left -= 1
        self._update_display()
        self._update_progress()
        if self.time_left <= 0:
            self._complete()
        else:
            self.timer_id = self.root.after(1000, self._tick)

    def _complete(self):
        self._pause()
        _play_async(DONE_CHIME if self.mode == "pomodoro" else BREAK_CHIME)
        _notify("Pomodoro Complete!" if self.mode == "pomodoro" else "Break Over!", "Time for a break!" if self.mode == "pomodoro" else "Back to work!")

        if self.mode == "pomodoro":
            self.completed += 1
            self.completed_label.config(text=f"Completed: {self.completed} sessions 🍅")
            if self.completed % self.goal == 0:
                nxt = "longBreak"
            else:
                nxt = "shortBreak"
        else:
            nxt = "pomodoro"

        self._set_mode(nxt)
        # Auto-start break after pomodoro, but not auto-start pomodoro after break
        if self.mode != "pomodoro":
            self.root.after(1000, self._start)

    def _update_display(self):
        m, s = divmod(self.time_left, 60)
        self.timer_text.config(text=f"{m:02d}:{s:02d}")

    def _update_progress(self):
        p = self.total_time > 0 and (self.total_time - self.time_left) / self.total_time or 0
        self.canvas.delete("all")
        cx, cy, r = 90, 90, 75
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#b8d4e3", width=6)
        extent = p * 359.99
        base_c = self.COLORS[self.mode]
        pv = getattr(self, '_pulse_val', 0.0)
        if self.running and pv > 0:
            arc_c = self._blend(base_c, self._lighten(base_c, 1.45), pv)
            arc_w = 6 + int(pv * 2.5)
        else:
            arc_c = base_c; arc_w = 6
        self.canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=90, extent=-extent,
                               outline=arc_c, width=arc_w, style="arc")

    def _update_color(self):
        c = self.COLORS[self.mode]
        self.timer_text.config(fg=c)
        self.title_label.config(fg=c)
        if hasattr(self, '_card_frame'):
            self._card_frame.config(highlightbackground=c)

    def _update_label(self):
        self.session_label.config(text=self.LABELS[self.mode])

    def _start_tray(self):
        _log("Starting system tray...")
        def run_tray():
            try:
                import pystray
                from PIL import Image
                if getattr(sys, 'frozen', False):
                    base = sys._MEIPASS
                else:
                    base = os.path.dirname(os.path.abspath(__file__))
                icon_path = os.path.join(base, "pomodoro_timer_icon.png")
                if os.path.exists(icon_path):
                    img = Image.open(icon_path).resize((64, 64), Image.LANCZOS)
                else:
                    img = Image.new("RGBA", (64, 64), (255, 0, 0, 255))

                def show_window():
                    self.root.after(0, lambda: (self.root.deiconify(), self.root.lift()))
                def start_timer():
                    self.root.after(0, self._start)
                def pause_timer():
                    self.root.after(0, self._pause)
                def reset_timer():
                    self.root.after(0, self._reset)
                def show_overlay():
                    self.root.after(0, self._show_overlay)
                def quit_app():
                    self.root.after(0, lambda: self._on_close(from_tray=True))

                self._tray_icon = pystray.Icon("pomodoro", img, "Pomodoro Timer", pystray.Menu(
                    pystray.MenuItem("Show", show_window, default=True),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Start", start_timer),
                    pystray.MenuItem("Pause", pause_timer),
                    pystray.MenuItem("Reset", reset_timer),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Show Overlay", show_overlay),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Quit", quit_app),
                ))

                _log("System tray icon created successfully")

                def tooltip_loop():
                    while True:
                        try:
                            m, s = divmod(self.time_left, 60)
                            st = "running" if self.running else "paused"
                            ml = {"pomodoro": "Work", "shortBreak": "Short", "longBreak": "Long"}
                            self._tray_icon.title = f"{m:02d}:{s:02d} {st} | {ml.get(self.mode, '?')}"
                        except:
                            pass
                        time.sleep(1)

                threading.Thread(target=tooltip_loop, daemon=True).start()
                self._tray_icon.run()
            except Exception as e:
                _log_error(f"System tray failed: {e}")

        threading.Thread(target=run_tray, daemon=True).start()

    def _on_close(self, from_tray=False):
        if from_tray:
            if self._tray_icon:
                try:
                    self._tray_icon.stop()
                except:
                    pass
            if hasattr(self, 'overlay_win') and self.overlay_win is not None:
                try:
                    if self.overlay_win.winfo_exists():
                        self.overlay_win.destroy()
                except:
                    pass
                self.overlay_win = None
                self.overlay_visible = False
            self.root.quit()
            self.root.destroy()
            import ctypes
            ctypes.windll.kernel32.ExitProcess(0)
        else:
            self.root.withdraw()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
