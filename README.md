# Pirate Shop Macro

A small Windows app that automates the Fortnite ready-up / return-to-lobby loop.
It clicks Ready, checks every 25 seconds whether you've been eliminated, leaves the
match, and repeats. It shows run time, deaths, average time per death, and a live
activity log in its own window.

> **Disclaimer:** This is an unofficial tool, not affiliated with or endorsed by Epic
> Games or NVIDIA. Automating gameplay may violate Epic's Terms of Service and
> accounts can be warned, restricted, or banned. Anti-cheat software can also flag
> simulated input. **Use at your own risk**, ideally not on an account you care about.
> It only reads your screen and sends clicks and key presses. It does not touch
> game files or memory.

---

## What it does

1. **Ready up:** finds `ready.png` on screen and clicks it (gives up after 15 s).
2. **Watch:** every 25 s it looks for `nvidia.png` (the NVIDIA Highlights button that
   shows when you're eliminated). It also looks for `failsafe.png`; if found, it clicks
   it, waits 5 s, then looks for `ready.png` again.
3. **Leave:** on elimination it presses **Esc**, clicks `menu.png`, then `leave.png`.
4. **Repeat.** It counts each death and remembers where it found each button, so
   later searches are faster.

## Requirements

- Windows 10 or 11
- [Python 3.10+](https://www.python.org/downloads/) (3.12 or 3.13 recommended; the very
  newest Python releases can lack compatible packages). Tick **"Add Python to PATH"**
  when installing.
- Fortnite in **Windowed Fullscreen** (borderless) so the macro can see it
- NVIDIA Highlights enabled if you use `nvidia.png` for elimination detection

## Setup

1. Download and unzip this folder anywhere.
2. Double-click **`Install Requirements.bat`** (one time only).
3. Add your screenshots to the **`images`** folder. See below.
4. Double-click **`pirate_shop_macro.pyw`** (or **`Start Pirate Shop Macro.bat`**).
5. Click **START**. You get 5 seconds to click into Fortnite.

## Screenshots (`images` folder)

The macro finds buttons by matching small pictures, so you need to make them yourself
for your own screen. Use these exact names:

| File | What to capture |
|---|---|
| `ready.png` | The Ready / Play button in the lobby |
| `nvidia.png` | The NVIDIA Highlights button shown when you're eliminated |
| `menu.png` | The menu button (take it *after* pressing Esc in a match) |
| `leave.png` | The Leave Match / Return to Lobby button |
| `failsafe.png` | Any extra button or popup to auto-click during a match |

**Tips for good screenshots**
- Press **Win + Shift + S**, crop tightly around the button or text (about 100-200 px wide).
- Don't include anything that changes: names, numbers, or game scenery.
- Capture at the same resolution and UI scale you'll play at.
- Too small or too generic a crop can cause false matches. Too large a crop can cause misses.

## Controls

| Action | How |
|---|---|
| Start | **START** button |
| Stop | **STOP** button, or press **F8** from anywhere |
| Emergency stop | Slam the mouse into any screen corner |
| Keep window visible | Tick **Always on top** |

## Settings

Open `pirate_shop_macro.pyw` in Notepad and edit the values near the top:

| Setting | Default | Meaning |
|---|---|---|
| `CHECK_INTERVAL` | 25 | Seconds between elimination checks |
| `CONFIDENCE` | 0.8 | Image match strictness (0-1). Lower if it misses buttons, raise if it misclicks |
| `READY_TIMEOUT` | 15 | Seconds to look for Ready before moving on |
| `LOBBY_WAIT` | 10 | Seconds to wait in the lobby after leaving |
| `FAILSAFE_READY_DELAY` | 5 | Seconds after the fail-safe click before checking for Ready |
| `REMEMBER_PAD` | 40 | Pixels of padding around a remembered button location |
| `REGIONS` | whole screen | Limit each search to a screen area `(left, top, width, height)` to cut CPU use |

The macro saves where it finds buttons in `locations.json`. Delete that file to reset.

## Make a standalone .exe (optional)

Double-click **`Build EXE.bat`**. It installs what it needs and creates
`Pirate Shop Macro.exe` in the same folder. Keep the `images` folder next to the exe.
The exe asks for administrator permission, which helps clicks register in-game.
Rebuild after editing any code.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Missing images" pop-up | Add the listed files to the `images` folder with the exact names |
| It never finds a button | Retake the screenshot at your real resolution; lower `CONFIDENCE` to ~0.7 |
| It clicks the wrong things | Use a tighter, more unique screenshot; raise `CONFIDENCE` to ~0.9 |
| Clicks or keys do nothing in-game | Run as administrator; use Windowed Fullscreen |
| Lag or high CPU | Set `REGIONS` for each button; raise `CHECK_INTERVAL` |
| Elimination never detected | Make sure NVIDIA Highlights is on, or use a different elimination image |
| Antivirus flags the exe | Common for programs that simulate input; build it yourself or add an exception |
| Package install fails | Install Python 3.12 or 3.13 instead of the newest release |

## Files

```
PirateShopMacro/
├── pirate_shop_macro.pyw        the app
├── Start Pirate Shop Macro.bat  alternate launcher
├── Install Requirements.bat     installs the Python packages
├── Build EXE.bat                builds a standalone .exe
├── requirements.txt             package list
├── logo.png / icon.ico          app logo and icon
├── images/                      YOUR screenshots go here
├── README.md
└── LICENSE
```

## License

MIT. See `LICENSE`.
