# DDT4ALL UI macOS build

`builddmg.sh` builds `DDT4ALL UI.app` with PyInstaller and packs it into a `.dmg`
using only the tools that ship with macOS (`hdiutil`, `ditto`). No `create-dmg` needed.

## Files

- `builddmg.sh` - builds the app and the dmg
- `entitlements.plist` - entitlements used by the shared PyInstaller spec (and by optional signing)
- the PyInstaller spec is shared by all platforms: `../pyinstaller/ddt4all.spec`

## Prerequisites

- macOS with Xcode Command Line Tools (`xcode-select --install`)
- Python 3.8+ with the project dependencies and PyInstaller already installed:
  ```bash
  pip install -e ".[can,network]" pyinstaller==6.22.3
  ```
  The script installs nothing and stops early if PyInstaller or `hdiutil` is missing.

## Build

Run from anywhere; pass the version without a leading `v`:

```bash
setup_tools/mac-os/builddmg.sh 3.1.3
```

Environment variables (optional):

- `PYTHON` - interpreter to use (default `python3`)
- `DDT4ALL_BUILD_DIR` - scratch root (default `<repo>/build`; only `macos-dmg/` inside it is wiped)
- `DDT4ALL_OUT_DIR` - output folder (default `<repo>/dist-packages`)
- `CODESIGN_IDENTITY` - re-sign the app with this identity before the dmg is made, e.g.
  `Developer ID Application: Your Name (XXXXXXXXXX)`. Without it the app keeps the
  ad-hoc signature PyInstaller applies. Notarization is not part of this script.

## Output

`dist-packages/DDT4ALL-UI-<VERSION>-macos-<arch>.dmg`, where `<arch>` is `uname -m`
(`arm64` on Apple Silicon, `x86_64` on Intel). The build is native to the machine it
runs on, not universal. The volume contains `DDT4ALL UI.app` and an `Applications`
symlink for drag-and-drop installation.

The Info.plist version is taken from `VERSION` (trimmed to dotted integers, so
`3.1.3-dev.42.abc1234` becomes `3.1.3`).

## Where the ECU database goes

The app looks for `ecu.zip` and `ecus/` in its working folder, which for the
bundled app is `~/Library/Application Support/ddt4all-ui` (created on first launch).
Override it with the `DDT4ALL_HOME` environment variable.

## Troubleshooting

- **"PyInstaller is not installed"**: `pip install pyinstaller` for the same Python the script uses (`PYTHON`).
- **"Gatekeeper blocks the app"**: the build is not notarized; right-click the app and choose Open, or sign it with `CODESIGN_IDENTITY`.
- **Debugging a crash**: build with `DDT4ALL_CONSOLE=1 setup_tools/mac-os/builddmg.sh X.Y.Z` to get a console build.
