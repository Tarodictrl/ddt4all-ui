# -*- mode: python ; coding: utf-8 -*-
"""Shared PyInstaller spec for DDT4ALL UI (Windows, Linux, macOS), onedir mode.

Run from anywhere:  python -m PyInstaller --noconfirm setup_tools/pyinstaller/ddt4all.spec

Environment switches:
  DDT4ALL_VERSION   version string for the macOS bundle (default: ddt4all.version)
  DDT4ALL_CONSOLE   "1" builds with a console window / stderr (CI smoke tests)
"""
import ast
import importlib.util
import os
import re
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# SPECPATH is injected by PyInstaller: the folder that holds this spec file.
ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
SRC = os.path.join(ROOT, "src")
PKG = os.path.join(SRC, "ddt4all")
PLUGINS = os.path.join(PKG, "plugins")
ICONS = os.path.join(ROOT, "resources", "icons")

# Make the build independent of how the package was installed (editable or not).
sys.path.insert(0, SRC)

APP_NAME = "DDT4ALL-UI"      # executable / onedir folder name (no space)
DISPLAY_NAME = "DDT4ALL UI"  # human-readable name (macOS bundle, Info.plist)
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
CONSOLE = os.environ.get("DDT4ALL_CONSOLE", "") == "1"


def _read_version():
    version = os.environ.get("DDT4ALL_VERSION", "").strip()
    if version:
        return version
    with open(os.path.join(PKG, "version.py"), encoding="utf-8") as f:
        match = re.search(r'^__version__\s*=\s*"([^"]+)"', f.read(), re.M)
    return match.group(1) if match else "0.0.0"


def _bundle_version(version):
    """CFBundleVersion must be dotted integers: '3.1.3-dev.abc1234' -> '3.1.3'."""
    match = re.match(r"\d+(\.\d+){0,2}", version)
    return match.group(0) if match else "0.0.0"


VERSION = _read_version()

# --- data files -------------------------------------------------------------
# collect_data_files("ddt4all") gives resources/*.json and the compiled
# generated/locales/*/LC_MESSAGES/*.mo, plus the non-.py plugin files (macros).
datas = list(collect_data_files("ddt4all"))

# Plugins are loaded from disk with SourceFileLoader (main_widget.py), so the
# .py sources must exist at <bundle>/ddt4all/plugins/ (incl. cmd_macros_lib).
_collected = {os.path.normcase(os.path.abspath(src)) for src, _dest in datas}
for dirpath, dirnames, filenames in os.walk(PLUGINS):
    dirnames[:] = [d for d in dirnames if d != "__pycache__"]
    for filename in filenames:
        if filename.endswith((".pyc", ".pyo")):
            continue
        src = os.path.join(dirpath, filename)
        if os.path.normcase(os.path.abspath(src)) in _collected:
            continue
        dest = os.path.join("ddt4all", "plugins", os.path.relpath(dirpath, PLUGINS))
        datas.append((src, os.path.normpath(dest)))

# Third-party licence texts (Lucide icons, ISC) ship next to the app, in
# <bundle>/licenses/. The About box mentions this path.
datas.append((os.path.join(ICONS, "svg", "LICENSE-lucide.txt"), "licenses"))

# --- hidden imports ---------------------------------------------------------
hiddenimports = list(collect_submodules("ddt4all"))

# Helper modules in plugins/cmd_macros_lib are put on sys.path and imported by
# plain name at run time, so PyInstaller cannot see what *they* import.
# Collect their third-party/stdlib imports explicitly.
_local = {"options", "file_manager", "elm", "ecu", "cmd_ui", "cmd_engine",
          "ddt4all_adapter", "can_addressing", "elm_log"}
for dirpath, dirnames, filenames in os.walk(PLUGINS):
    dirnames[:] = [d for d in dirnames if d != "__pycache__"]
    for filename in filenames:
        if not filename.endswith(".py"):
            continue
        try:
            with open(os.path.join(dirpath, filename), encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                top = name.split(".")[0]
                if top in _local or top == "ddt4all" or name in hiddenimports:
                    continue
                try:
                    found = importlib.util.find_spec(top) is not None
                except (ImportError, ValueError):
                    found = False
                if found:  # optional deps that are not installed are skipped
                    hiddenimports.append(name)

# Optional dependencies (python-can, obd, bluetooth, WebEngine...) are picked up
# by PyInstaller's import analysis only when installed; a missing one must not
# fail the build, so nothing is forced here.

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    pathex=[SRC],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "_pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # native arch of the runner (arm64 on macos-14)
    codesign_identity=None,
    entitlements_file=(
        os.path.join(ROOT, "setup_tools", "mac-os", "entitlements.plist") if IS_MAC else None
    ),
    icon=os.path.join(ICONS, "obd.ico") if IS_WIN else (
        os.path.join(ICONS, "obd.icns") if IS_MAC else None
    ),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

if IS_MAC:
    _bv = _bundle_version(VERSION)
    app = BUNDLE(
        coll,
        name=DISPLAY_NAME + ".app",
        icon=os.path.join(ICONS, "obd.icns"),
        bundle_identifier="com.github.tarodictrl.ddt4all-ui",
        version=_bv,
        info_plist={
            "CFBundleName": DISPLAY_NAME,
            "CFBundleDisplayName": DISPLAY_NAME,
            "CFBundleShortVersionString": _bv,
            "CFBundleVersion": _bv,
            "CFBundleExecutable": APP_NAME,
            "CFBundleIdentifier": "com.github.tarodictrl.ddt4all-ui",
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundlePackageType": "APPL",
            "CFBundleSignature": "DDT4",
            "LSMinimumSystemVersion": "10.13.0",
            "LSApplicationCategoryType": "public.app-category.developer-tools",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,  # dark mode supported
            "NSHumanReadableCopyright": "Copyright ©2016-2026 Cedric PAILLE",
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeExtensions": ["ddt"],
                    "CFBundleTypeName": DISPLAY_NAME + " Project File",
                    "CFBundleTypeRole": "Editor",
                    "LSHandlerRank": "Owner",
                }
            ],
            # Hardware access descriptions
            "NSBluetoothAlwaysUsageDescription": DISPLAY_NAME + " needs Bluetooth access to communicate with OBD adapters.",
            "NSBluetoothPeripheralUsageDescription": DISPLAY_NAME + " needs Bluetooth access to communicate with OBD adapters.",
            "NSLocationWhenInUseUsageDescription": DISPLAY_NAME + " may use location services for enhanced diagnostic features.",
            "NSUSBDeviceUsageDescription": DISPLAY_NAME + " needs USB access to communicate with OBD adapters.",
        },
    )
