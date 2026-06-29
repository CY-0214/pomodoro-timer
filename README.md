# 🍅 Pomodoro Timer

A beautiful, lightweight Pomodoro Timer desktop application built with Python and tkinter. Features a floating overlay, system tray integration, automatic cycle management, and customizable background.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)

## 📸 Screenshot

- Light blue theme with rounded card UI
- Pill-shaped mode buttons with hover effects
- Circular progress ring with pulse animation
- Floating overlay window (always on top)
- System tray integration with live timer tooltip

## 🚀 Download

Download the latest release: **[PomodoroTimer.exe](https://github.com/CY-0214/pomodoro-timer/releases/latest/download/PomodoroTimer.exe)**

No installation required — just download and run!

## ✨ Features

- **Pomodoro Technique** — 25min work, 5min short break, 15min long break
- **Auto Cycle** — Automatically runs through 4 pomodoros: 25>5>25>5>25>5>25>15
- **Floating Overlay** — Compact always-on-top timer window, drag to reposition
- **System Tray** — Minimize to tray, right-click for quick controls
- **Sound Effects** — Audio notifications for start, break, and completion
- **Desktop Notifications** — Windows toast notifications
- **Customizable Durations** — Adjust pomodoro, break, and cycle settings
- **Session Tracking** — Count completed pomodoro sessions
- **Background Image** — Supports custom background.png
- **Pill-shaped Mode Buttons** — With hover effects and active state highlighting
- **Pulse Animation** — Progress ring pulses while timer is running
- **Slide-in Settings** — Smooth animated settings panel

## 🎮 Usage

1. Download `PomodoroTimer.exe` from the [Releases](https://github.com/CY-0214/pomodoro-timer/releases) page
2. Double-click to run
3. Click **Start** to begin a pomodoro session
4. The timer will auto-cycle through work and breaks
5. Close the window to minimize to system tray
6. Right-click the tray icon for quick controls

### Controls

| Action | How |
|--------|-----|
| Start/Pause/Reset | Buttons in main window or right-click tray icon |
| Show Overlay | Settings ⚙ → Show Overlay, or right-click tray → Show Overlay |
| Hide Overlay | Right-click overlay → Hide Overlay |
| Quick controls | Right-click tray icon → Start / Pause / Reset |
| Quit | Right-click tray icon → Quit |

### Settings

Click ⚙ to customize:
- Pomodoro duration (1-120 min)
- Short break duration (1-120 min)
- Long break duration (1-120 min)
- Cycles before long break (1-20)

### Overlay Right-Click Menu

- Show Timer — restore main window
- Start / Pause / Reset — quick timer controls
- Hide Overlay — hide the floating overlay
- Quit — exit completely

## 🔧 Build from Source

```bash
# Clone the repo
git clone https://github.com/CY-0214/pomodoro-timer.git
cd pomodoro-timer

# Install dependencies
pip install pystray Pillow plyer pyinstaller

# Run directly
python pomodoro_timer.py

# Build EXE
pyinstaller PomodoroTimer.spec
```

## 📁 Project Structure

```
pomodoro-timer/
├── pomodoro_timer.py      # Main application
├── PomodoroTimer.spec     # PyInstaller build spec
├── tomato_icon.ico        # Application icon (EXE file icon)
├── icon_256.png           # Taskbar + tray icon
├── background.png         # Window background image (optional)
├── CHANGELOG.md           # Version history
├── README.md              # This file
└── LICENSE                # MIT License
```

## 📝 License

MIT License — free to use, modify, and distribute.

## ⚠️ Windows Defender / Antivirus

When you first run `PomodoroTimer.exe`, Windows Defender Smartscreen shows a warning because the EXE is **unsigned** (no code signing certificate).

This is a **false positive** — the app is open source and safe.

### Option 1 — Click "Run anyway"
On the warning screen, click **"More info"** then **"Run anyway"**. This only appears once.

### Option 2 — Add Windows Defender exclusion (recommended)

Run this command in **PowerShell as Administrator**:

```powershell
Add-MpPreference -ExclusionPath "C:\Path\To\Your\PomodoroTimer.exe"
```

Replace the path with wherever you saved the EXE. After this, no more warnings.

### Option 3 — Add exclusion via Windows Security GUI

1. Open **Windows Security**
2. Go to **Virus & threat protection**
3. Click **Manage settings**
4. Scroll down to **Exclusions** → Click **Add or remove exclusions**
5. Click **Add an exclusion** → **File**
6. Select `PomodoroTimer.exe`

### Option 4 — Unblock the file

Right-click `PomodoroTimer.exe` → **Properties** → Check **"Unblock"** at the bottom → Click **OK**
