#!/usr/bin/env bash
# Build DDT4ALL .deb and .rpm packages (PyInstaller onedir + fpm).
#
# Usage:   setup_tools/linux/build-packages.sh VERSION
#   VERSION   release version WITHOUT a leading "v", e.g. 3.1.3 or 3.1.3-dev.abc1234
#
# Can be run from any directory. Installs nothing: every tool below must already
# be on PATH, otherwise the script stops early with a clear message.
#
# Required tools:
#   python3 (or $PYTHON) with the project dependencies and PyInstaller installed
#   fpm      (gem install fpm)
#   rpmbuild (apt-get install rpm) - used by fpm to produce the .rpm
#
# Environment variables (all optional):
#   PYTHON               Python interpreter to use                 (default: python3)
#   DDT4ALL_BUILD_DIR    scratch root; this script uses <dir>/linux-packages
#                        and wipes only that sub-folder             (default: <repo>/build)
#   DDT4ALL_OUT_DIR      where the packages are written             (default: <repo>/dist-packages)
#
# Outputs, in $DDT4ALL_OUT_DIR (<arch> = `uname -m`, x86_64 on CI):
#   DDT4ALL-<VERSION>-linux-<arch>.deb
#   DDT4ALL-<VERSION>-linux-<arch>.rpm
#
# Package version mapping. "-" is reserved in deb/rpm version fields, and a plain
# "3.1.3-dev.x" would sort AFTER the final "3.1.3", so:
#   the first "-" becomes "~" (pre-release, sorts before 3.1.3), further "-" become ".":
#     3.1.3                 -> 3.1.3
#     3.1.3-dev.abc1234     -> 3.1.3~dev.abc1234
#     3.1.3-rc.1            -> 3.1.3~rc.1
#   fpm appends release/iteration "1" (deb 3.1.3-1, rpm 3.1.3-1).
#   Package name: ddt4all.
#
# Installed layout:
#   /opt/ddt4all/                                   PyInstaller onedir contents (DDT4ALL binary)
#   /usr/bin/ddt4all                                sh wrapper: exec /opt/ddt4all/DDT4ALL "$@"
#   /usr/share/applications/ddt4all.desktop
#   /usr/share/icons/hicolor/256x256/apps/ddt4all.png
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
    echo "usage: $0 VERSION   (e.g. 3.1.3 or 3.1.3-dev.abc1234, no leading 'v')" >&2
    exit 2
fi
VERSION="$1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PYTHON:-python3}"
BUILD_ROOT="${DDT4ALL_BUILD_DIR:-$ROOT/build}"
OUT_DIR="${DDT4ALL_OUT_DIR:-$ROOT/dist-packages}"
SPEC="$ROOT/setup_tools/pyinstaller/ddt4all.spec"
ICON="$ROOT/resources/icons/obd.png"
ARCH="$(uname -m)"

# --- version mapping --------------------------------------------------------
case "$VERSION" in
    [vV]*) die "VERSION must not start with 'v' (got '$VERSION')" ;;
esac
tilde='~'
PKG_VERSION="${VERSION/-/$tilde}"   # first "-" -> "~"
PKG_VERSION="${PKG_VERSION//-/.}"   # remaining "-" -> "."
if ! [[ "$PKG_VERSION" =~ ^[0-9][0-9A-Za-z.+~]*$ ]]; then
    die "version '$VERSION' (mapped to '$PKG_VERSION') is not valid for deb/rpm"
fi

# --- tool checks ------------------------------------------------------------
command -v "$PYTHON" >/dev/null 2>&1 || die "'$PYTHON' not found on PATH"
"$PYTHON" -m PyInstaller --version >/dev/null 2>&1 \
    || die "PyInstaller is not installed for '$PYTHON' (pip install pyinstaller)"
command -v fpm >/dev/null 2>&1 || die "fpm not found on PATH (gem install fpm)"
command -v rpmbuild >/dev/null 2>&1 || die "rpmbuild not found on PATH (apt-get install rpm)"
[ -f "$SPEC" ] || die "missing $SPEC"
[ -f "$ICON" ] || die "missing $ICON"

WORK="$BUILD_ROOT/linux-packages"
PYI_DIST="$WORK/pyinstaller/dist"
PYI_WORK="$WORK/pyinstaller/work"
STAGE="$WORK/stage"
SCRIPTS="$WORK/scripts"

rm -rf "$WORK"
mkdir -p "$PYI_DIST" "$PYI_WORK" "$STAGE" "$SCRIPTS" "$OUT_DIR"

# --- 1. PyInstaller ---------------------------------------------------------
echo "==> PyInstaller (version $VERSION)"
DDT4ALL_VERSION="$VERSION" "$PYTHON" -m PyInstaller --noconfirm --clean \
    --distpath "$PYI_DIST" --workpath "$PYI_WORK" "$SPEC"
[ -x "$PYI_DIST/DDT4ALL/DDT4ALL" ] || die "PyInstaller did not produce $PYI_DIST/DDT4ALL/DDT4ALL"

# --- 2. stage the package tree ---------------------------------------------
echo "==> Staging package tree"
mkdir -p "$STAGE/opt" "$STAGE/usr/bin" "$STAGE/usr/share/applications" \
         "$STAGE/usr/share/icons/hicolor/256x256/apps"
cp -a "$PYI_DIST/DDT4ALL" "$STAGE/opt/ddt4all"

cat > "$STAGE/usr/bin/ddt4all" <<'WRAPPER'
#!/bin/sh
exec /opt/ddt4all/DDT4ALL "$@"
WRAPPER
chmod 755 "$STAGE/usr/bin/ddt4all"

cat > "$STAGE/usr/share/applications/ddt4all.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=DDT4All
Comment=ECU diagnostic and parameter screen tool
Exec=ddt4all
Icon=ddt4all
Categories=Development;Electronics;
Terminal=false
DESKTOP
chmod 644 "$STAGE/usr/share/applications/ddt4all.desktop"

# The source icon is 272x272; hicolor/256x256 should hold exactly 256x256.
# PyQt5 is a project dependency, so use it to scale; fall back to a plain copy.
ICON_DEST="$STAGE/usr/share/icons/hicolor/256x256/apps/ddt4all.png"
if ! "$PYTHON" - "$ICON" "$ICON_DEST" <<'PYEOF' 2>/dev/null
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage
img = QImage(sys.argv[1])
if img.isNull():
    sys.exit(1)
img = img.scaled(256, 256, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
sys.exit(0 if img.save(sys.argv[2], "PNG") else 1)
PYEOF
then
    echo "warning: could not scale the icon to 256x256, copying it unchanged" >&2
    install -m 644 "$ICON" "$ICON_DEST"
fi
chmod 644 "$ICON_DEST"

# Readable by everyone, writable by the owner only (fpm maps the owner to root).
chmod -R go-w,a+rX "$STAGE"

cat > "$SCRIPTS/after-install.sh" <<'POSTINST'
#!/bin/sh
# Refresh desktop/icon caches when the tools exist; never fail the install.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
POSTINST
chmod 755 "$SCRIPTS/after-install.sh"

# --- 3. fpm -----------------------------------------------------------------
DESCRIPTION="$("$PYTHON" - "$ROOT/pyproject.toml" <<'PYEOF'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r'^description\s*=\s*"([^"]*)"', text, re.M)
print(m.group(1) if m else "DDT4All ECU diagnostic tool")
PYEOF
)"

fpm_common=(
    -s dir
    --force
    -n ddt4all
    -v "$PKG_VERSION"
    --iteration 1
    -a "$ARCH"
    --license "GPL-3.0-or-later"
    --url "https://github.com/Tarodictrl/ddt4all-ui"
    --maintainer "DDT4All contributors"
    --vendor "DDT4All"
    --description "$DESCRIPTION"
    --directories /opt/ddt4all
    --after-install "$SCRIPTS/after-install.sh"
    -C "$STAGE"
)

DEB="$OUT_DIR/DDT4ALL-$VERSION-linux-$ARCH.deb"
RPM="$OUT_DIR/DDT4ALL-$VERSION-linux-$ARCH.rpm"

echo "==> fpm: $DEB"
fpm "${fpm_common[@]}" -t deb -p "$DEB" \
    --deb-user root --deb-group root \
    -d libxcb-xinerama0 -d libxkbcommon-x11-0 -d libgl1 \
    -d libglib2.0-0 -d libfontconfig1 -d libdbus-1-3 \
    .

echo "==> fpm: $RPM"
fpm "${fpm_common[@]}" -t rpm -p "$RPM" \
    --rpm-user root --rpm-group root \
    -d libxkbcommon-x11 -d mesa-libGL -d glib2 -d fontconfig -d dbus-libs \
    .

[ -s "$DEB" ] || die "deb was not created: $DEB"
[ -s "$RPM" ] || die "rpm was not created: $RPM"

if command -v dpkg-deb >/dev/null 2>&1; then
    dpkg-deb --info "$DEB" || true
fi
ls -l "$OUT_DIR"
echo "Done:"
echo "  $DEB"
echo "  $RPM"
