#!/usr/bin/env bash
# Build DDT4ALL.app (PyInstaller) and package it into a .dmg with hdiutil.
#
# Usage:   setup_tools/mac-os/builddmg.sh VERSION
#   VERSION   release version WITHOUT a leading "v", e.g. 3.1.3 or 3.1.3-dev.42.abc1234
#             (the Info.plist bundle version is trimmed to dotted integers by the spec)
#
# Can be run from any directory. Installs nothing: python3 (or $PYTHON) with the
# project dependencies and PyInstaller, plus the macOS tools hdiutil and ditto,
# must already be available, otherwise the script stops early.
#
# Environment variables (all optional):
#   PYTHON               Python interpreter to use                 (default: python3)
#   DDT4ALL_BUILD_DIR    scratch root; this script uses <dir>/macos-dmg
#                        and wipes only that sub-folder             (default: <repo>/build)
#   DDT4ALL_OUT_DIR      where the dmg is written                   (default: <repo>/dist-packages)
#   CODESIGN_IDENTITY    if set, DDT4ALL.app is re-signed with this identity
#                        (codesign --deep, hardened runtime, entitlements.plist)
#                        before the dmg is created. Unset = whatever signature
#                        PyInstaller applied (ad-hoc on Apple Silicon).
#
# Output, in $DDT4ALL_OUT_DIR (<arch> = `uname -m`, arm64 on a macos-15 runner):
#   DDT4ALL-<VERSION>-macos-<arch>.dmg
#   The volume holds DDT4ALL.app and an "Applications" symlink for drag-and-drop.
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }
info() { echo "==> $*"; }

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
    echo "usage: $0 VERSION   (e.g. 3.1.3 or 3.1.3-dev.42.abc1234, no leading 'v')" >&2
    exit 2
fi
VERSION="$1"
case "$VERSION" in
    [vV]*) die "VERSION must not start with 'v' (got '$VERSION')" ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PYTHON:-python3}"
BUILD_ROOT="${DDT4ALL_BUILD_DIR:-$ROOT/build}"
OUT_DIR="${DDT4ALL_OUT_DIR:-$ROOT/dist-packages}"
SPEC="$ROOT/setup_tools/pyinstaller/ddt4all.spec"
ENTITLEMENTS="$SCRIPT_DIR/entitlements.plist"
ARCH="$(uname -m)"
DMG="$OUT_DIR/DDT4ALL-$VERSION-macos-$ARCH.dmg"

# --- tool checks ------------------------------------------------------------
[ "$(uname -s)" = "Darwin" ] || die "this script must run on macOS"
command -v "$PYTHON" >/dev/null 2>&1 || die "'$PYTHON' not found on PATH"
"$PYTHON" -m PyInstaller --version >/dev/null 2>&1 \
    || die "PyInstaller is not installed for '$PYTHON' (pip install pyinstaller)"
command -v hdiutil >/dev/null 2>&1 || die "hdiutil not found (macOS only)"
command -v ditto >/dev/null 2>&1 || die "ditto not found (macOS only)"
[ -f "$SPEC" ] || die "missing $SPEC"
[ -f "$ROOT/resources/icons/obd.icns" ] || die "missing $ROOT/resources/icons/obd.icns"

WORK="$BUILD_ROOT/macos-dmg"
PYI_DIST="$WORK/pyinstaller/dist"
PYI_WORK="$WORK/pyinstaller/work"
STAGE="$WORK/stage"

rm -rf "$WORK"
mkdir -p "$PYI_DIST" "$PYI_WORK" "$STAGE" "$OUT_DIR"

# --- 1. PyInstaller ---------------------------------------------------------
info "PyInstaller (version $VERSION)"
DDT4ALL_VERSION="$VERSION" "$PYTHON" -m PyInstaller --noconfirm --clean \
    --distpath "$PYI_DIST" --workpath "$PYI_WORK" "$SPEC"
APP="$PYI_DIST/DDT4ALL.app"
[ -d "$APP" ] || die "PyInstaller did not produce $APP"
info "App size: $(du -sh "$APP" | cut -f1)"
# Non-fatal: PyInstaller ad-hoc signs the bundle; report it if the signature is not intact.
codesign --verify --deep --strict "$APP" \
    || echo "warning: codesign --verify reported a problem for $APP (continuing)" >&2

# --- 2. optional code signing ----------------------------------------------
if [ -n "${CODESIGN_IDENTITY:-}" ]; then
    info "Signing with identity: $CODESIGN_IDENTITY"
    codesign --force --deep --options runtime --timestamp \
        --entitlements "$ENTITLEMENTS" --sign "$CODESIGN_IDENTITY" "$APP"
    codesign --verify --deep --strict --verbose=2 "$APP"
else
    echo "note: CODESIGN_IDENTITY is not set; the app is not re-signed (ad-hoc signature only)" >&2
fi

# --- 3. stage and build the dmg --------------------------------------------
info "Staging dmg contents"
ditto "$APP" "$STAGE/DDT4ALL.app"
ln -s /Applications "$STAGE/Applications"

rm -f "$DMG"
# hdiutil create sometimes fails with "Resource busy" on GitHub macOS runners: retry.
info "hdiutil create: $DMG"
attempt=1
max_attempts=5
until hdiutil create -volname "DDT4ALL" -srcfolder "$STAGE" -ov -format UDZO "$DMG"; do
    if [ "$attempt" -ge "$max_attempts" ]; then
        die "hdiutil create failed after $max_attempts attempts"
    fi
    delay=$((attempt * 5))
    echo "warning: hdiutil create failed (attempt $attempt/$max_attempts); retrying in ${delay}s" >&2
    sleep "$delay"
    rm -f "$DMG"
    attempt=$((attempt + 1))
done
[ -s "$DMG" ] || die "dmg was not created: $DMG"

if hdiutil verify "$DMG" >/dev/null 2>&1; then
    info "dmg verification passed"
else
    echo "warning: hdiutil verify reported a problem for $DMG" >&2
fi

ls -l "$OUT_DIR"
echo "Done: $DMG"
