# DDT4ALL

[![Build packages](https://github.com/Tarodictrl/ddt4all-ui/actions/workflows/build.yml/badge.svg)](https://github.com/Tarodictrl/ddt4all-ui/actions/workflows/build.yml)
[![Tests](https://github.com/Tarodictrl/ddt4all-ui/actions/workflows/python-app.yml/badge.svg)](https://github.com/Tarodictrl/ddt4all-ui/actions/workflows/python-app.yml)
[![Latest release](https://img.shields.io/github/v/release/Tarodictrl/ddt4all-ui?label=release)](https://github.com/Tarodictrl/ddt4all-ui/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-GPL%203.0-green.svg)](license.txt)

DDT4ALL is a cross-platform diagnostic application for CAN bus vehicle networks.
It lets you **create your own ECU parameter screens** and **communicate with ECUs**
through various OBD-II interfaces, including ELM327, Vlinker FS, VGate iCar Pro,
OBDLink SX/EX and ELS27 adapters.

> **This is a fork of [cedricp/ddt4all](https://github.com/cedricp/ddt4all)** with a redesigned
> user interface (Fluent light/dark theme, live charts) and ready-made packages for
> Windows, Linux and macOS built by CI. Diagnostic functionality comes from upstream;
> the original author and contributors are credited [below](#credits-and-support).

- **Current version:** `v3.1.3` (Celestial Nemean)
- **License:** [GPL-3.0-or-later](license.txt)

---

## Warnings

- This application is **work in progress**. Use **Expert mode** only if you know what you are doing.
- In **non-expert** mode the tool is meant to be harmless for the vehicle (keep the Expert mode button in its released state).
- **Do not use this software if you do not understand how a CAN network (or an ECU) works** — serious damage is possible on a live vehicle.
- Maintenance, testing and research only; the author declines responsibility for any use. **You are responsible.**

---

## What's new in this fork

### Fluent theme

A light Fluent-style look with a matching dark variant, applied from a single QSS
template. Switch it in **View → Theme** (*Light Theme* / *Dark Theme*). The status bar
shows a connection pill (`CONNECTED` / `DISCONNECTED` / `EDITION MODE`), the protocol,
scan messages and the refresh rate / CAN timeout fields.

### Live charts

A bottom **Charts** dock plots ECU parameters in real time, one lane per parameter
(own Y scale, shared time axis and cursor).

1. Open an ECU screen and start polling (connect an adapter or use simulation).
2. **Right-click a value** on the screen and choose **Add to chart** (up to 8 lanes;
   use *Remove from chart* or the lane's `×` to drop one).
3. Pick the window: **30 / 60 / 120 / 300 s**. **Pause** freezes the view while data
   keeps buffering; while paused the **mouse wheel** scrolls back in time. **Resume** returns to now.
4. **CSV** exports the whole buffer of all lanes; **Clear** empties the data but keeps the lanes.

Show or hide the dock via **View → Panels → Charts** or the *Charts* toolbar button.
Dock layout and the chart window size are restored on the next start.
To try the panel without an adapter: `python -m ddt4all.ui.charts.demo [--dark]`.

---

## Download

Get the file for your platform from the
[**latest release**](https://github.com/Tarodictrl/ddt4all-ui/releases/latest)
(`<version>` is the release number, e.g. `3.1.3`).

| Platform | File | Install |
|----------|------|---------|
| Windows x64 installer | `DDT4ALL-<version>-windows-x64-setup.exe` | Run the installer |
| Windows x86 (32-bit) installer | `DDT4ALL-<version>-windows-x86-setup.exe` | Run the installer |
| Windows portable | `DDT4ALL-<version>-windows-x64-portable.zip` | Unzip to a writable folder, run `DDT4ALL\DDT4ALL.exe` |
| Debian / Ubuntu | `DDT4ALL-<version>-linux-x86_64.deb` | `sudo apt install ./DDT4ALL-<version>-linux-x86_64.deb` |
| Fedora / RHEL / openSUSE | `DDT4ALL-<version>-linux-x86_64.rpm` | `sudo dnf install ./DDT4ALL-<version>-linux-x86_64.rpm` |
| Linux AppImage | `DDT4ALL-<version>-linux-x86_64.AppImage` | `chmod +x DDT4ALL-<version>-linux-x86_64.AppImage` then run it |
| macOS (Apple Silicon) | `DDT4ALL-<version>-macos-arm64.dmg` | Open the dmg, drag `DDT4ALL` to *Applications* |

Notes:

- **macOS** builds are not signed or notarized. On first launch use right-click →
  **Open**, or remove the quarantine flag:
  `xattr -dr com.apple.quarantine /Applications/DDT4ALL.app`
- **AppImage** needs FUSE (`libfuse2` on recent Ubuntu/Debian).
- **Linux**: add your user to the `dialout` group for serial adapters (see [Platform notes](#platform-notes)).
- **Test builds:** every pull request and every push to `master` builds all packages
  as CI artifacts, kept for 14 days: GitHub → **Actions** → *Build packages* → pick a run →
  **Artifacts**. Their version looks like `3.1.3-dev.<commit>`.

---

## ECU database location

DDT4ALL does **not** ship the ECU database. It looks for `ecu.zip` (or an extracted
`ecus/` folder with `eculist.xml`) in its **working directory**, which depends on the build:

| Build | Put `ecu.zip` / `ecus/` in |
|-------|----------------------------|
| Windows portable zip | the folder that contains `DDT4ALL.exe` |
| Windows installer (x64 / x86) | the install folder (default `C:\Program Files\DDT4ALL`); the shortcuts start the app there. **The installer deletes this folder on reinstall, upgrade and uninstall, so keep a copy of `ecu.zip` elsewhere.** |
| `.deb` / `.rpm` | `~/.local/share/ddt4all/` (created on first run; honours `XDG_DATA_HOME`) |
| macOS `.dmg` | `~/Library/Application Support/ddt4all/` (created on first run) |
| AppImage | `~/.local/share/ddt4all/` (created on first run; honours `XDG_DATA_HOME`) |
| Run from source | the directory you run `python -m ddt4all` from |

The PyInstaller builds (portable zip, `.deb`, `.rpm`, `.dmg`) start through a small launcher
([`launcher.py`](setup_tools/pyinstaller/launcher.py)) that switches to the folder above before the
app starts; the AppImage's `AppRun` does the same for its data folder. Set `DDT4ALL_HOME` to use another folder:

```bash
DDT4ALL_HOME=/data/ddt4all ddt4all             # Linux / macOS
```
```powershell
$env:DDT4ALL_HOME = "D:\ddt4all"; .\DDT4ALL.exe   # Windows portable
```

`DDT4ALL_HOME` is read by that launcher and by the AppImage's `AppRun`; the Windows installer runs
`python -m ddt4all` directly and ignores it. The normal builds have no console window; for
troubleshooting build with `DDT4ALL_CONSOLE=1` (see [Building packages locally](#building-packages-locally)).

---

## Features

- **Modern UI**: Fluent light/dark theme, restyled status bar and live charts (see [What's new](#whats-new-in-this-fork)).
- **Diagnostics**: Read / Clear DTC, manual ECU requests, auto-scan ECUs, live parameter monitoring.
- **Screens**: Custom ECU parameter screens designer, screen recorder, data editor.
- **Networks**: CAN bus sniffing (with live non-blocking capture), DoIP, KWP2000.
- **Database**: XML + ZIP (auto `ecu.zip`), JSON internal conversion, graphics extraction.
- **Automation**: Plugin system (vehicle-specific procedures) and extensible Python CLI.
- **Internationalization**: gettext/polib catalogs in 14 languages, real-time switch, HTML-aware strings.

---

## Supported devices

| Device | Available speeds | Default baud | Timeout | Flow control | Category | Notes |
|--------|------------------|--------------|---------|--------------|----------|-------|
| VLinker FS | 57600, 115200 | 38400 | 3 s | None | Enhanced | Most stable, best compatibility |
| VGate iCar Pro | 115200, 230400, 500000, 1000000 | 115200 | 2 s | None | Enhanced | High-speed (up to 1 000 000 bps) |
| ELM327 (original) | standard | 38400 | 5 s | None | General | Usually marked `PIC18F25K80` |
| ELM327 (clone) | standard | 9600–38400 | 5 s | None | Budget | Try different baud settings |
| ELM327 USB | standard | 38400 | 5 s | None | USB | Dedicated ELM327 USB (`STD_USB`) |
| OBDLink SX | 500k / 1M / 2M | 115200 | 2 s | RTS/CTS | Professional | Highest-speed adapter |
| OBDLink EX | 500k / 1M / 2M | 115200 | 2 s | RTS/CTS | Professional | Tested and confirmed |
| ELS27 | standard | 38400 | 4 s | None | Alternative | Good ELM327 equivalent |
| ELS27 V5 | standard | 38400 | 4 s | None | Enhanced | CAN pins 12-13, PyRen / Renolink compatible |
| DERLEK USB-DIAG2/3 | standard | 38400 | 4 s | None | Professional | Auto pin swap, STN/STPX support * |
| USB CAN | varies | 38400 | 5 s | None | Special | Automatic detection / fallback |

> \* DERLEK USB-DIAG2/3 status: not checked on real hardware yet.

### Connection methods

- **USB** — recommended for diagnostics (serial-over-USB on a COM/LPT port).
- **Bluetooth** — convenient, occasional dropouts possible.
- **WiFi** — TCP/IP, `IP:PORT` format (e.g. `192.168.0.10:35000`).

> Most adapters appear as a standard serial port. Dedicated USB-CAN / USB-ELM327
> devices are handled natively with an automatic fallback.

---

## Language support

gettext catalogs are authored under `locales/` and compiled into
`src/ddt4all/generated/locales/`. English is the source language (used as `msgid`);
the following catalogues are shipped:

| Code | Language |
|------|----------|
| `fr` | Français |
| `pt` | Português |
| `de` | Deutsch |
| `es` | Español |
| `it` | Italiano |
| `ru` | Русский |
| `pl` | Polski |
| `nl` | Nederlands |
| `hu` | Magyar |
| `ro` | Română |
| `sr` | Српски |
| `tr` | Türkçe |
| `cs_CZ` | Czech |
| `uk_UA` | Українська |

All catalogs are complete (content of all `msgstr` fields is present
and no `#, fuzzy` remains), keep valid gettext syntax and preserve the original
`%s` / named placeholders.

---

## Run from source

Requirements:

- **Python** `>=3.8` (3.10 or newer recommended)
- **PyQt5** `>=5.15, <5.16` — GUI framework
- **PyQtWebEngine** `>=5.15, <5.16` — optional, full HTML documentation view
- **pyserial** `==3.5` — serial port communication
- **pyusb** `==1.2.1` — USB access
- **crcmod** `==1.7` — checksums
- **polib**, **platformdirs**
- **pywin32** `>=227` — Windows (serial)

```bash
git clone https://github.com/Tarodictrl/ddt4all-ui.git
cd ddt4all-ui
python -m venv ./venv

# activate the virtual environment
#   Windows:        .\venv\Scripts\activate.bat
#   Linux / macOS:  source ./venv/bin/activate

pip install -e ".[dev]"      # the package plus pytest and linting tools
python -m ddt4all            # or simply: ddt4all
```

Charts demo without an adapter: `python -m ddt4all.ui.charts.demo [--dark]`.
Tests: `QT_QPA_PLATFORM=offscreen pytest` (Windows PowerShell:
`$env:QT_QPA_PLATFORM="offscreen"; pytest`).

Other extras: `.[can]` (python-can, obd), `.[network]` (requests, websockets),
`.[bluetooth]` (pybluez / bleak); combine them, e.g. `pip install -e ".[dev,can,network,bluetooth]"`.
Plain `pip install -e .` installs only the runtime dependencies. Without the project
installed, the dependencies can be added by hand:

```bash
pip install "PyQt5>=5.15,<5.16" "PyQtWebEngine>=5.15,<5.16" pyserial==3.5 pyusb==1.2.1 crcmod==1.7 polib platformdirs
```

### Windows: virtualenv path with non-ASCII characters

Qt 5 cannot load its `platform` plugin when the virtualenv path contains non-ASCII
characters (for example a Cyrillic folder name): the app stops with
*"could not find or load the Qt platform plugin"*. Create the venv in an ASCII path:

```powershell
python -m venv C:\venvs\ddt4all
C:\venvs\ddt4all\Scripts\pip install -e ".[dev]"
C:\venvs\ddt4all\Scripts\python -m ddt4all
```

The source checkout itself can stay where it is.

### Windows: no wheel for PyQt5-Qt5

If pip cannot find a Windows wheel for `PyQt5-Qt5` >= 5.15.19, pin the older Qt binaries:

```bash
pip install PyQt5-Qt5==5.15.2 PyQtWebEngine-Qt5==5.15.2
pip install -e ".[dev]"
```

### Platform notes

- **Linux** — add the current user to the `dialout` group to access serial ports:
  ```bash
  sudo usermod -a -G dialout $USER
  # logout and login again
  ```
- **Windows** — ensure the serial/USB drivers are installed and that a COM port is
  assigned to the adapter. Run with administrator rights if port access fails.
- **macOS** — if an editable-install error is raised by `pip install -e .`, update the
  packaging tools first:
  ```bash
  python3 -m pip install --upgrade pip setuptools wheel
  python3 -m pip install -e .
  ```
  If the package data is missing at runtime (`resources/projects.json not found`),
  reinstall from the repository root:
  ```bash
  python3 -m pip install --force-reinstall -e .
  ```

### Quick start

Start DDT4ALL, then use the built-in **connection test** to let it auto-detect the adapter
and the correct baud rate. On discovery, the optimal device configuration is applied.

---

## Plugin system

Vehicle-specific procedures are provided as Python modules under
`src/ddt4all/plugins/`:

- `ab90_reset.py` — AB90 air-bag reset
- `card_programming.py` — ECU card programming
- `clio3_eps_reset.py`, `clio4_eps_reset.py` — Clio 3/4 EPS reset
- `cmd_macros.py` — DDT2000 command macros (`.cmd`, uses `cmd_macros_lib/`)
- `laguna2_uch_reset.py`, `laguna3_uch_reset.py` — Laguna 2/3 UCH
- `megane2_uch_reset.py`, `megane3_uch_reset.py` — Megane 2/3 UCH
- `megane3_ab_reset.py` — Megane 3 air-bag reset
- `megane3_eps_reset.py` — Megane 3 EPS
- `rsat4_reset.py` — RSAT4 system reset
- `vin_crc.py` — VIN CRC calculation
- `zoe_waterpump_counter_reset.py` — ZOE water-pump counting reset

The plugin architecture allows custom procedures for other ECUs and brands.

---

## Architecture

### Core modules

- `src/ddt4all/main.py` — entry point (PyQt GUI + connection handling)
- `src/ddt4all/version.py` — version / codename / contributors
- `src/ddt4all/options.py` — configuration & device settings persistence
- `src/ddt4all/file_manager.py` — file and directory utilities
- `src/ddt4all/cli/` — command-line interface handlers (DoIP, parameters, USB device)

### Communication

- `core/elm/` — ELM327 / adapter communication (`elm.py`, `device_manager.py`,
  `port.py`, `constants.py`)
- `core/ecu/` — ECU database, files and scanning (`ecu_database.py`,
  `ecu_scanner.py`, `ecu_device.py`, `ecu_file.py`, `ecu_request.py`,
  `ecu_ident.py`, `data_item.py`, `utils.py`)
- `core/doip/` — DoIP (Diagnostics over IP) protocol support
- `core/parameters/helpers.py` — parameter parsing / helpers
- `core/usbdevice/` — USB CAN devices (`obd_device.py`, `usb_can.py`, `constants.py`)

### Modern UI

- `ui/` — main window, widgets, dialogs
- `ui/theme/` — light/dark palettes and the QSS template (`resources/styles/fluent.qss`)
- `ui/charts/` — live charts panel (time-series buffer, lane view, CSV export, `demo.py`)
- `ui/displaymod/` — display widgets / graphical elements
- `ui/data_editor/` — ECU qualitative data editing
- `ui/sniffer/` — CAN sniffing with a QThread-based thread

### Data & resources

- `generated/` — compiled resources and `.mo` translation catalogs
- `resources.qrc` — Qt resource descriptor
- `vehicles/` — vehicle-specific files
- `json/` — JSON database folder
- `logs/` — runtime logs (see also the platform user-log directory)

### Threading

- QThread for the network sniffer (non-blocking capture)
- `threading.Lock()` in the ELM layer for safe serial operations
- `QTimer` for periodic refresh and connection monitoring

---

## Testing

```bash
pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen pytest
```

Test suites are in `tests/` (`unit`, `integration`, `smoke`). The `python-app.yml`
workflow runs them on Linux, Windows and macOS for every pull request and every push to `master`.

---

## Building packages locally

All scripts take the version **without** a leading `v` (`3.1.3`, or `3.1.3-dev.abc1234`)
and write to `dist-packages/` (git-ignored); scratch files go to `build/`.
Optional environment variables: `PYTHON` (interpreter), `DDT4ALL_BUILD_DIR`, `DDT4ALL_OUT_DIR`.
The scripts install nothing: install the project and PyInstaller first
(`pip install -e ".[can,network]" pyinstaller`). All PyInstaller builds share
[`setup_tools/pyinstaller/ddt4all.spec`](setup_tools/pyinstaller/ddt4all.spec); set
`DDT4ALL_CONSOLE=1` before building to get a build that prints to a console.

| Target | Command | Output | Extra tools |
|--------|---------|--------|-------------|
| Windows portable | `powershell -NoProfile -ExecutionPolicy Bypass -File setup_tools/windows/build-portable.ps1 3.1.3` | `dist-packages/DDT4ALL-3.1.3-windows-x64-portable.zip` | PyInstaller |
| Linux deb + rpm | `bash setup_tools/linux/build-packages.sh 3.1.3` | `dist-packages/DDT4ALL-3.1.3-linux-x86_64.deb` and `.rpm` | PyInstaller, `fpm` (`gem install fpm`), `rpmbuild` (`apt install rpm`) |
| macOS dmg | `bash setup_tools/mac-os/builddmg.sh 3.1.3` | `dist-packages/DDT4ALL-3.1.3-macos-<arch>.dmg` | PyInstaller, `hdiutil` (built in); optional `CODESIGN_IDENTITY` |
| Linux AppImage | `bash setup_tools/appimage/build.sh 3.1.3` | `ddt4all-3.1.3-x86_64.AppImage` in the repo root (CI renames it to `DDT4ALL-3.1.3-linux-x86_64.AppImage`) | `wget`; bundles the active Python environment |
| Windows installer | `ISCC.exe setup_tools\inno-win-setup\wininstaller.iss` (32-bit: `wininstaller-py3.8.6-inno-5-32-bits.iss`) | `setup_tools/inno-win-setup/Output/DDT4ALL-Windows-Installer-v<version>_Celestial-Nemean-<arch>.exe` | Inno Setup 6.2.2 (32-bit script: 5.6.1) and a prepared Python copy, see below |

The Windows installer bundles a full Python. Before compiling, copy a Python install that
already has the project dependencies (`pip install -e ".[dev,can,network,bluetooth]"`) to
`\DDT4ALL-Dist-Versions\Python313` on the drive root (32-bit script: `\DDT4ALL-Dist-Versions\Python38-32`).
The installer takes its version from `setup_tools/inno-win-setup/version.h`.
More details: [`setup_tools/README.md`](setup_tools/README.md), [`setup_tools/mac-os/README.md`](setup_tools/mac-os/README.md).

---

## Releasing

1. Bump `__version__` in `src/ddt4all/version.py`; keep `pyproject.toml` and
   `setup_tools/inno-win-setup/version.h` in sync.
2. Commit and merge to `master`.
3. Tag and push:
   ```bash
   git tag v3.1.4
   git push origin v3.1.4
   ```
4. The *Build packages* workflow ([`build.yml`](.github/workflows/build.yml)) builds all seven
   packages, and its `release` job publishes a GitHub Release with generated notes and every
   file attached. The tag name without `v` becomes the version in the file names.

GitHub Actions must be enabled once on the fork (**Actions** tab → enable workflows);
until then no workflow runs. Only tags starting with `v` create a release.

---

## Troubleshooting

### Connection

- **No serial port listed** — check driver installation. On Linux, verify the user
  is in the `dialout` group. On Windows, try running as administrator.
- **Adapter not detected** — test every available COM/USB port with the connection
  test; try another baud rate (38400, 9600, 115200).
- **ELS27 V5 special case** — check the driver (PyRen / Reolink), then select the
  proper serial port manually (device may appear as `FTDI`, `CH340` or `CP210x`).
- **WiFi** — format `IP:PORT`, same local network, firewall open.

### Installation

- **PyQtWebEngine missing** — DDT4All still works; only the full web-based
  documentation view is limited (graceful fallback).
- **Windows serial fails** — reinstall `pywin32` and run
  `python -m pywin32_postinstall -install`, ideally with admin rights.

## Documentation & videos

See the upstream [Wiki](https://github.com/cedricp/ddt4all/wiki) (Android port,
device notes) and the YouTube channel (CAN sniffing, AirBag DTC, Megane examples).
Module reference: [`documentation/`](documentation/).

## Credits and support

DDT4ALL was created by **Cedric Paille** ([cedricp/ddt4all](https://github.com/cedricp/ddt4all)) and
is developed with the help of many contributors (see `__contributors__` in
[`src/ddt4all/version.py`](src/ddt4all/version.py)). This fork adds the redesigned UI and the packaging pipeline.

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=cedricpaille%40gmail.com&item_name=codetronic&currency_code=EUR&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHosted)
[![Sponsor](https://img.shields.io/badge/💖%20Sponsor-Support%20upstream-ea4aaa)](https://github.com/sponsors/Furtif)
[![Discord](https://img.shields.io/discord/1117970325267820675?label=Discord&style=flat-square)](https://discord.gg/cBqDh9bTHP)

- **Discord (upstream community)**: [Join](https://discord.gg/cBqDh9bTHP)
- **Fork issues** (UI, charts, packages, CI): [Tarodictrl/ddt4all-ui issues](https://github.com/Tarodictrl/ddt4all-ui/issues)
- **Upstream issues** (diagnostics core, devices): [cedricp/ddt4all issues](https://github.com/cedricp/ddt4all/issues)
- **Upstream discussions**: [GitHub Discussions](https://github.com/cedricp/ddt4all/discussions)

### Contributing

- **Report bugs** — add a screenshot, your `Logs/` file, `[Bug]` in the title, OS + Python + adapter info.
- **Suggestions / ideas** — open an issue or discussion with `[Suggestion]` in the title.
- **Translations** — improve or add language catalogs under `locales/`.
- **Donations** — financial (PayPal / GitHub Sponsors) and hardware donations
  (OBD-II interfaces, ECU devices) to the upstream project help extend device support.

---

## License & disclaimer

This project is **free software** under the **GPL-3.0-or-later** license. DDT4ALL is
an independent, unofficial, educational tool and is *not* affiliated with any
vehicle/software brand. It is provided for study, testing and research only; it is
not a replacement for factory/bench diagnostic tools. Use on a real vehicle is at
your own risk — see the warnings at the top of this file.

**Happy CAN studying!** 🚗🔧
