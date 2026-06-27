# 🍅 Pomodoro Timer

A beautiful, lightweight Pomodoro Timer desktop application built with Python and tkinter. Features a floating overlay, system tray integration, and automatic cycle management.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)

## 📸 Screenshot

- Dark theme with glass-morphism UI
- Circular progress ring with color-coded modes
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
- **Sound Effects** — Audio notifications for start, tick, break, and completion
- **Desktop Notifications** — Windows toast notifications
- **Customizable Durations** — Adjust pomodoro, break, and cycle settings
- **Session Tracking** — Count completed pomodoro sessions

## 🎮 Usage

1. Download `PomodoroTimer.exe` from the [Releases](https://github.com/YOUR_USERNAME/pomodoro-timer/releases) page
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

## 🔧 Build from Source

```bash
# Clone the repo
git clone https://github.com/CY-0214/pomodoro-timer.git
cd pomodoro-timer

# Install dependencies
pip install pystray Pillow plyer

# Run directly
python pomodoro_timer.py

# Build EXE
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "icon_256.png;." --icon=tomato_icon.ico pomodoro_timer.py
```

## 📁 Project Structure

```
pomodoro-timer/
├── pomodoro_timer.py    # Main application
├── tomato_icon.ico      # Application icon
├── icon_256.png         # Taskbar icon
├── Start Pomodoro.bat   # Launcher (alternative)
├── README.md            # This file
└── LICENSE              # MIT License
```

## 📝 License

MIT License — free to use, modify, and distribute.

## ⚠️ Antivirus Note

Windows Defender or antivirus software may flag the EXE as suspicious. This is a **false positive** caused by PyInstaller bundling. The code is open source — you can verify it yourself. Click "Run anyway" to use the app.
