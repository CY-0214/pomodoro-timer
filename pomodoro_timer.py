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
        import tkinter as tk

        self.root = tk.Tk()
        self.root.title("Pomodoro Timer")
        self.root.geometry("370x480")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

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

        self.COLORS = {"pomodoro": "#ff6b6b", "shortBreak": "#2ecc71", "longBreak": "#5dade2"}
        self.LABELS = {"pomodoro": "Pomodoro Session", "shortBreak": "Short Break", "longBreak": "Long Break"}

        # UI
        self._build_ui()
        self._update_display()
        self._update_progress()
        self._update_color()

        # System tray
        self._tray_icon = None
        self._start_tray()

        # Handle close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Set taskbar icon
        self._set_taskbar_icon()

    def _set_taskbar_icon(self):
        """Set the taskbar icon from the bundled resource."""
        try:
            if getattr(sys, 'frozen', False):
                base = sys._MEIPASS
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base, "icon_256.png")
            if os.path.exists(icon_path):
                import tkinter as tk
                from PIL import Image, ImageTk
                img = Image.open(icon_path)
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
                self._icon_photo = photo  # prevent garbage collection
        except:
            pass

    def _build_ui(self):
        import tkinter as tk

        # Top bar
        top_frame = tk.Frame(self.root, bg="#1a1a2e")
        top_frame.pack(fill="x", padx=10, pady=(10, 0))

        # Settings button
        self.settings_btn = tk.Label(top_frame, text="⚙", font=("Segoe UI", 14), bg="#1a1a2e", fg="#888", cursor="hand2")
        self.settings_btn.pack(side="left")
        self.settings_btn.bind("<Button-1>", self._toggle_settings)
        self.settings_btn.bind("<Enter>", lambda e: self.settings_btn.config(fg="#fff"))
        self.settings_btn.bind("<Leave>", lambda e: self.settings_btn.config(fg="#888"))

        # Settings panel (hidden initially)
        self.settings_frame = tk.Frame(self.root, bg="#19192d", bd=0)
        # Don't pack yet - hidden

        tk.Label(self.settings_frame, text="⏱ Durations (min)", font=("Segoe UI", 10, "bold"), bg="#19192d", fg="#fff").pack(anchor="w", pady=(8, 6), padx=8)

        self.s_vars = {}
        for key, label, default in [("pomodoro", "Pomodoro:", 25), ("shortBreak", "Short Break:", 5), ("longBreak", "Long Break:", 15)]:
            row = tk.Frame(self.settings_frame, bg="#19192d")
            row.pack(fill="x", padx=8, pady=2)
            tk.Label(row, text=label, font=("Segoe UI", 9), bg="#19192d", fg="#999", width=14, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(default))
            entry = tk.Entry(row, textvariable=var, width=6, font=("Segoe UI", 9), bg="#2a2a3e", fg="#fff", insertbackground="#fff", relief="flat", justify="center")
            entry.pack(side="left")
            self.s_vars[key] = var

        # Cycles
        row = tk.Frame(self.settings_frame, bg="#19192d")
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text="Cycles:", font=("Segoe UI", 9), bg="#19192d", fg="#999", width=14, anchor="w").pack(side="left")
        self.s_cycle_var = tk.StringVar(value="4")
        entry = tk.Entry(row, textvariable=self.s_cycle_var, width=6, font=("Segoe UI", 9), bg="#2a2a3e", fg="#fff", insertbackground="#fff", relief="flat", justify="center")
        entry.pack(side="left")
        self.s_vars["cycle"] = self.s_cycle_var

        # Overlay toggle in settings
        overlay_row = tk.Frame(self.settings_frame, bg="#19192d")
        overlay_row.pack(fill="x", padx=8, pady=(10, 2))
        self.overlay_toggle_btn = tk.Button(overlay_row, text="Show Overlay", font=("Segoe UI", 9, "bold"), bg="#4ecdc4", fg="#1a1a2e", relief="flat", cursor="hand2", command=self._toggle_overlay)
        self.overlay_toggle_btn.pack(fill="x")

        apply_btn = tk.Button(self.settings_frame, text="Apply", font=("Segoe UI", 9, "bold"), bg="#4ecdc4", fg="#1a1a2e", relief="flat", cursor="hand2", command=self._apply_settings)
        apply_btn.pack(fill="x", padx=8, pady=(8, 8))

        self.s_err = tk.Label(self.settings_frame, text="Durations: 1-120, Cycles: 1-20", font=("Segoe UI", 8), bg="#19192d", fg="#ff6b6b")
        self.s_err.pack_forget()

        # Title
        self.title_label = tk.Label(self.root, text="🍅 Pomodoro Timer", font=("Segoe UI", 16, "bold"), bg="#1a1a2e", fg="#ff6b6b")
        self.title_label.pack(pady=(10, 8))

        # Mode buttons
        mode_frame = tk.Frame(self.root, bg="#1a1a2e")
        mode_frame.pack(pady=(0, 10))
        self.mode_buttons = {}
        for mode in ["pomodoro", "shortBreak", "longBreak"]:
            label = "Pomodoro" if mode == "pomodoro" else "Short Break" if mode == "shortBreak" else "Long Break"
            btn = tk.Button(mode_frame, text=label, font=("Segoe UI", 9), bg="#2a2a3e", fg="#fff", relief="flat", cursor="hand2",
                           command=lambda m=mode: self._set_mode(m))
            btn.pack(side="left", padx=3)
            self.mode_buttons[mode] = btn

        # Progress ring (canvas)
        self.canvas = tk.Canvas(self.root, width=180, height=180, bg="#1a1a2e", highlightthickness=0)
        self.canvas.pack(pady=(0, 5))

        # Timer text - centered on canvas using place with canvas coordinates
        self.timer_text = tk.Label(self.canvas, text="25:00", font=("Consolas", 28, "bold"), bg="#1a1a2e", fg="#ff6b6b")
        self.timer_text.place(relx=0.5, rely=0.5, anchor="center")

        # Controls
        ctrl_frame = tk.Frame(self.root, bg="#1a1a2e")
        ctrl_frame.pack(pady=(10, 5))

        self.reset_btn = tk.Button(ctrl_frame, text="Reset", font=("Segoe UI", 12, "bold"), bg="#ff6b6b", fg="white", relief="flat", cursor="hand2", width=10, command=self._reset)
        self.reset_btn.pack(side="right", padx=5)

        self.start_btn = tk.Button(ctrl_frame, text="Start", font=("Segoe UI", 12, "bold"), bg="#4ecdc4", fg="#1a1a2e", relief="flat", cursor="hand2", width=10, command=self._start)
        self.start_btn.pack(side="right", padx=5)

        self.pause_btn = tk.Button(ctrl_frame, text="Pause", font=("Segoe UI", 12, "bold"), bg="#ffd93d", fg="#1a1a2e", relief="flat", cursor="hand2", width=10, command=self._pause)
        self.pause_btn.pack_forget()

        # Session info
        self.session_label = tk.Label(self.root, text="Pomodoro Session", font=("Segoe UI", 10), bg="#1a1a2e", fg="#aaa")
        self.session_label.pack(pady=(5, 2))

        self.completed_label = tk.Label(self.root, text="Completed: 0 sessions 🍅", font=("Segoe UI", 9), bg="#1a1a2e", fg="#777")
        self.completed_label.pack()

        # Click outside settings to close
        self.root.bind("<Button-1>", self._on_click_outside)

    def _on_click_outside(self, event):
        if hasattr(self, 'settings_frame') and self.settings_frame.winfo_viewable():
            if event.widget not in [self.settings_frame, self.settings_btn] and not self._is_child_of(event.widget, self.settings_frame):
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
        if self.settings_frame.winfo_viewable():
            self._close_settings()
        else:
            self.settings_frame.pack(fill="x", padx=10, pady=(0, 10), before=self.title_label)
            # Expand window height to fit settings
            self.root.geometry("370x600")

    def _close_settings(self):
        self.settings_frame.pack_forget()
        self.s_err.pack_forget()
        self.root.geometry("370x480")

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
            self._hide_overlay()
        else:
            self._show_overlay()

    def _show_overlay(self):
        if self.overlay_visible:
            return
        self.overlay_visible = True
        self.overlay_toggle_btn.config(text="Hide Overlay")

        # Create overlay in a separate thread (can't have two Tk() in same thread)
        def create_overlay():
            import tkinter as tk
            self.overlay_win = tk.Tk()
            self.overlay_win.title("")
            self.overlay_win.overrideredirect(True)
            self.overlay_win.attributes("-topmost", True)
            self.overlay_win.configure(bg="#1a1a2e")
            self.overlay_win.resizable(False, False)

            # Position bottom-right of screen, smaller and shifted right
            sw = self.overlay_win.winfo_screenwidth()
            sh = self.overlay_win.winfo_screenheight()
            self.overlay_win.geometry(f"100x45+{sw-105}+{sh-80}")

            # Overlay widgets — compact layout
            top_frame = tk.Frame(self.overlay_win, bg="#1a1a2e")
            top_frame.pack(fill="x", padx=4, pady=(2, 0))
            self.overlay_session = tk.Label(top_frame, text="WORK", font=("Segoe UI", 7, "bold"), bg="#1a1a2e", fg="#ff6b6b")
            self.overlay_session.pack(side="left")
            self.overlay_time = tk.Label(self.overlay_win, text="25:00", font=("Consolas", 14, "bold"), bg="#1a1a2e", fg="#ff6b6b")
            self.overlay_time.pack(pady=(0, 2))

            # Drag support
            drag = {"x": 0, "y": 0}
            def start_drag(e):
                drag["x"] = e.x; drag["y"] = e.y
            def do_drag(e):
                self.overlay_win.geometry(f"+{self.overlay_win.winfo_x()+e.x-drag['x']}+{self.overlay_win.winfo_y()+e.y-drag['y']}")
            for w in [self.overlay_win, self.overlay_session, self.overlay_time]:
                w.bind("<Button-1>", start_drag)
                w.bind("<B1-Motion>", do_drag)

            # Right-click menu (same as system tray)
            self.overlay_menu = tk.Menu(self.overlay_win, tearoff=0, bg="#1a1a2e", fg="#ffffff",
                                         activebackground="#ff6b6b", activeforeground="#ffffff")
            self.overlay_menu.add_command(label="Show Timer", command=self._show_timer_from_overlay)
            self.overlay_menu.add_separator()
            self.overlay_menu.add_command(label="Start", command=self._overlay_start_safe)
            self.overlay_menu.add_command(label="Pause", command=self._overlay_pause_safe)
            self.overlay_menu.add_command(label="Reset", command=self._overlay_reset_safe)
            self.overlay_menu.add_separator()
            self.overlay_menu.add_command(label="Hide Overlay", command=self._overlay_hide_safe)
            self.overlay_menu.add_separator()
            self.overlay_menu.add_command(label="Quit", command=self._overlay_quit_safe)

            for w in [self.overlay_win, self.overlay_session, self.overlay_time]:
                w.bind("<Button-3>", self._show_overlay_menu)

            # Start overlay update loop
            self._update_overlay()
            self.overlay_win.mainloop()

        t = threading.Thread(target=create_overlay, daemon=True)
        t.start()

    def _overlay_hide_safe(self):
        """Called from overlay thread to safely hide overlay.
        Schedules the destroy on the overlay thread itself."""
        try:
            if hasattr(self, 'overlay_win') and self.overlay_win is not None:
                self.overlay_win.after(0, self._destroy_overlay)
        except:
            pass

    def _overlay_start_safe(self):
        """Called from overlay thread to start timer."""
        try:
            self.root.after(0, self._start)
        except:
            pass

    def _overlay_pause_safe(self):
        """Called from overlay thread to pause timer."""
        try:
            self.root.after(0, self._pause)
        except:
            pass

    def _overlay_reset_safe(self):
        """Called from overlay thread to reset timer."""
        try:
            self.root.after(0, self._reset)
        except:
            pass

    def _destroy_overlay(self):
        """Run inside overlay thread to safely close the overlay window."""
        try:
            if hasattr(self, 'overlay_win') and self.overlay_win is not None:
                self.overlay_win.destroy()
        except:
            pass
        # Notify main thread to update state
        try:
            self.root.after(0, self._finish_hide_overlay)
        except:
            pass

    def _finish_hide_overlay(self):
        """Update UI state after overlay is destroyed."""
        self.overlay_visible = False
        if hasattr(self, 'overlay_toggle_btn'):
            self.overlay_toggle_btn.config(text="Show Overlay")
        self.overlay_win = None

    def _overlay_quit_safe(self):
        """Called from overlay thread to safely quit the whole app."""
        try:
            if hasattr(self, 'overlay_win') and self.overlay_win is not None:
                self.overlay_win.after(0, self.overlay_win.destroy)
        except:
            pass
        try:
            self.root.after(0, lambda: self._on_close(from_tray=True))
        except:
            pass

    def _show_overlay_menu(self, event):
        try:
            self.overlay_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.overlay_menu.grab_release()

    def _show_timer_from_overlay(self):
        self.root.deiconify()
        self.root.lift()

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
            label = self.LABELS[self.mode]
            self.overlay_session.config(text=label, fg=c)
            self.overlay_time.config(fg=c)
        except:
            pass
        try:
            self.overlay_win.after(1000, self._update_overlay)
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
        for m, btn in self.mode_buttons.items():
            if m == self.mode:
                btn.config(bg=self.COLORS[m])
            else:
                btn.config(bg="#2a2a3e")

    def _start(self):
        self.running = True
        self.start_btn.pack_forget()
        self.pause_btn.pack(side="left", padx=5)
        _play_async(START_CHIME)
        self._tick()

    def _pause(self):
        self.running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.pause_btn.pack_forget()
        self.start_btn.pack(side="left", padx=5)

    def _reset(self):
        self._pause()
        self.time_left = self.durations[self.mode] * 60
        self.total_time = self.time_left
        self._update_display()
        self._update_progress()

    def _tick(self):
        if not self.running:
            return
        if self.time_left > 0:
            self.time_left -= 1
            self._update_display()
            self._update_progress()
            if self.time_left <= 3 and self.time_left > 0:
                _play_async(TICK_CHIME)
            self.timer_id = self.root.after(1000, self._tick)
        else:
            self._complete()

    def _complete(self):
        self._pause()
        _play_async(DONE_CHIME if self.mode == "pomodoro" else BREAK_CHIME)
        
        if self.mode == "pomodoro":
            self.completed += 1
            self.completed_label.config(text=f"Completed: {self.completed} sessions 🍅")
            _notify("Pomodoro Complete!", f"{self.completed} done. Time for a break!")
            # After pomodoro → always go to break (short or long)
            nxt = "longBreak" if self.completed % self.goal == 0 else "shortBreak"
        else:
            _notify("Break Over", "Focus time! You got this!")
            # After long break → cycle complete, stop and wait for user
            if self.mode == "longBreak":
                self._set_mode("pomodoro")
                return  # Don't auto-start, wait for user
            # After short break → auto-start next pomodoro
            nxt = "pomodoro"

        self._set_mode(nxt)
        # Auto-start next timer (break or pomodoro in middle of cycle)
        self.root.after(1000, self._start)

    def _update_display(self):
        m = self.time_left // 60
        s = self.time_left % 60
        self.timer_text.config(text=f"{m:02d}:{s:02d}")

    def _update_progress(self):
        p = self.total_time > 0 and (self.total_time - self.time_left) / self.total_time or 0
        self.canvas.delete("all")
        cx, cy, r = 90, 90, 70
        color = self.COLORS[self.mode]
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#2a2a3e", width=6)
        if p > 0:
            extent = 360 * p
            self.canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=90, extent=-extent, style="arc", outline=color, width=6)

    def _update_color(self):
        c = self.COLORS[self.mode]
        self.title_label.config(fg=c)
        self.timer_text.config(fg=c)
        self._update_mode_buttons()

    def _update_label(self):
        self.session_label.config(text=self.LABELS[self.mode])

    def _start_tray(self):
        def run_tray():
            try:
                import pystray
                from PIL import Image

                # Load icon from resource
                if getattr(sys, 'frozen', False):
                    base = sys._MEIPASS
                else:
                    base = os.path.dirname(os.path.abspath(__file__))
                icon_path = os.path.join(base, "icon_256.png")
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
                # Log errors to a file for debugging
                with open(os.path.join(tempfile.gettempdir(), "pomodoro_tray_error.txt"), "w") as f:
                    import traceback
                    f.write(traceback.format_exc())

        threading.Thread(target=run_tray, daemon=True).start()

    def _on_close(self, from_tray=False):
        if from_tray:
            # Quit completely from tray menu - stop everything
            # Stop the tray icon
            if self._tray_icon:
                try:
                    self._tray_icon.stop()
                except:
                    pass
            # Destroy overlay if visible
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
            # Minimize to tray — hide window but keep running
            self.root.withdraw()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
