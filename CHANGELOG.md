# Changelog

All notable changes to the Pomodoro Timer project.

---

## [dist33] — 2026-06-28

### Changed
- **Color scheme**: Changed from dark theme (`#1a1a2e`) to light blue theme (`#e8f4f8`) to match user's background image tone
- Background: `BG_COLOR = "#e8f4f8"`, Text: `#2c3e50`, Accent: `#3498db`
- Buttons: Blue primary, red reset, yellow pause
- Settings panel: Light blue `#d0e0e8`

### Fixed
- **Overlay menu commands**: All menu commands in overlay are now LOCAL functions inside `create_overlay()` thread, preventing `AttributeError` for missing methods
- **Overlay hide/show**: Uses `withdraw()` / `deiconify()` instead of destroy/recreate, preventing crash on second show
- **Overlay position**: Set to `+{sw-102}+{sh-78}` (user-adjusted)

---

## [dist28] — 2026-06-28

### Fixed
- **Overlay crash on second show**: Changed from `destroy()` + recreate to `withdraw()` + `deiconify()`
- **Overlay position**: User-adjusted to `+{sw-102}+{sh-78}`

---

## [dist23] — 2026-06-28

### Fixed
- **Overlay menu AttributeError**: Replaced `self._show_overlay_menu`, `self._overlay_start_safe` etc. with local functions inside `create_overlay()` that callback via `self.root.after(0, ...)`

---

## [dist21] — 2026-06-28

### Fixed
- **Overlay `_show_timer_from_overlay` missing**: Added the missing method

---

## [dist13] — 2026-06-28

### Added
- **Logging**: Added `_log()` and `_log_error()` functions writing to `~/pomodoro_log.txt`
- **Overlay debug logging**: Added detailed logging inside `create_overlay()` to trace failures

### Fixed
- **System tray icon**: Built with Hermes venv Python (has pystray) instead of clean Python 3.14

---

## [dist9] — 2026-06-27

### Features
- Pure tkinter GUI (no HTML/pywebview)
- Floating overlay in separate thread
- System tray with pystray
- Auto-cycle: 25>5>25>5>25>5>25>15 then stop
- Taskbar icon via PIL ImageTk
- Sound effects (start, tick, done, break)
- Settings panel with duration customization

---

## Build Versions (dist10–dist32)

Various intermediate builds during debugging:
- dist10–dist12: Python 3.14 clean env builds (PIL._imaging not bundled, tray failed)
- dist13–dist20: Added logging, traced overlay AttributeError
- dist21: Fixed missing `_show_timer_from_overlay`
- dist22: Still had `self._show_overlay_menu` error
- dist23: Fixed all overlay menu commands to local functions
- dist24–dist28: User-adjusted overlay position
- dist29–dist31: Background image attempts (stipple, canvas create_image)
- dist32: Reverted background, light blue color scheme
- dist33: Final light blue theme with all fixes
