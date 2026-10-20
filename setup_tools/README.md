# DDT4All Build Tools

This directory contains comprehensive build and packaging tools for creating distributable DDT4All applications across different platforms.

## Overview

DDT4All uses modern Python packaging with `pyproject.toml` and provides automated build scripts for creating platform-specific installers:

- **Windows**: InnoSetup-based installer with embedded Python runtime, plus a PyInstaller portable zip (`windows/build-portable.ps1`)
- **macOS**: PyInstaller-based DMG (`mac-os/builddmg.sh`)
- **Linux**: `.deb` / `.rpm` (`linux/build-packages.sh`) and AppImage (`appimage/build.sh`)

Releases are built by CI (`.github/workflows/build.yml`); see the "Building packages locally"
and "Releasing" sections of the main README for the exact commands and output names.
All PyInstaller builds share `pyinstaller/ddt4all.spec`.

## Prerequisites

### Common Requirements
- **Python 3.8+** (3.10+ recommended)
- **Git** for version control
- **Development tools** for your platform

### Platform-Specific Requirements

#### Windows
- **InnoSetup 6.0+** - [Download Here](https://jrsoftware.org/isdl.php)
- **Microsoft Visual Studio Build Tools** (for some dependencies)
- **Windows SDK** (for installer signing, optional)

#### macOS
- **Xcode Command Line Tools**: `xcode-select --install`
- **PyInstaller**: `pip install pyinstaller`

#### Linux
- **Build essentials**: `sudo apt-get install build-essential`
- **Python development headers**: `sudo apt-get install python3-dev`

## Windows Build Process

### 1. Prepare Environment
```bash
# Clone repository
git clone https://github.com/cedricp/ddt4all.git
cd ddt4all

# Create virtual environment
python -m venv ./venv
.\venv\Scripts\activate.bat

# Install dependencies
pip install -e .
```

### 2. Update Version Information
Edit `setup_tools/inno-win-setup/version.h`:
```c
#define __appname__ "DDT4ALL"
#define __version__ "3.0.7"
#define __status__ "Kakapo"
#define __author__ "Cedric PAILLE"
#define __copyright__ "Copyright 2016-2026"
#define __email__ "cedricpaille@gmail.com"
```

### 3. Build Installer
```bash
# Navigate to setup tools directory
cd setup_tools/inno-win-setup

# Compile with InnoSetup (GUI)
# Open wininstaller.iss in InnoSetup and compile

# Or compile via command line
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" wininstaller.iss
```

### 4. Output
- **Installer**: `DDT4ALL-Windows-Installer-v3.0.7_Kakapo-x64.exe`
- **Location**: Same directory as the `.iss` file
- **Size**: ~150-200MB (includes Python runtime)

### Windows Installer Features
- **Embedded Python 3.13** runtime
- **Automatic dependency management**
- **Desktop shortcut creation**
- **Start menu integration**
- **Uninstaller with complete cleanup**
- **User permission management** for logs and data directories

## macOS Build Process

### 1. Prepare Environment
```bash
# Clone repository
git clone https://github.com/cedricp/ddt4all.git
cd ddt4all

# Create virtual environment
python3 -m venv ./venv
source ./venv/bin/activate

# Upgrade packaging tools (recommended on macOS)
python3 -m pip install --upgrade pip setuptools wheel

# Install dependencies including PyInstaller
pip install -e ".[dev]"
pip install pyinstaller
```

### 2. Build Application
```bash
# From the repository root; VERSION has no leading "v"
bash setup_tools/mac-os/builddmg.sh 3.1.3
```
See `mac-os/README.md` for details (the old `main.spec` and `create-dmg` are no longer used).

### 5. Output
- **DMG**: `dist-packages/DDT4ALL-<version>-macos-<arch>.dmg`
- **Architecture**: native to the build machine (CI builds Apple Silicon)

### macOS Build Features
- **Code signing** support (with appropriate certificates)
- **Notarization** ready (entitlements.plist included)
- **Standalone application** with embedded dependencies
- **Proper macOS integration** (dock, menus, etc.)

## Linux Build Process

### Development Installation (Recommended)
```bash
# Clone and install
git clone https://github.com/cedricp/ddt4all.git
cd ddt4all

# Create virtual environment
python3 -m venv ./venv
source ./venv/bin/activate

# Install in development mode
pip install -e .

# Create desktop entry
cat > ~/.local/share/applications/ddt4all.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=DDT4ALL
Comment=ECU diagnostic tool
Exec=$(pwd)/venv/bin/ddt4all
Icon=$(pwd)/src/ddt4all/resources/icons/obd.ico
Terminal=false
Categories=Development;Science;
EOF
```

### Package Building (Advanced)
```bash
# Needs PyInstaller, fpm (gem install fpm) and rpmbuild (apt-get install rpm)
bash setup_tools/linux/build-packages.sh 3.1.3

# Output in dist-packages/: DDT4ALL-3.1.3-linux-x86_64.deb and .rpm
```

## Version Management

### Automatic Version Sync
The build systems automatically sync version information from:
- `src/ddt4all/version.py` (primary source)
- `pyproject.toml` (package version)
- `setup_tools/inno-win-setup/version.h` (Windows installer)

### Version Update Process
1. Update `src/ddt4all/version.py`
2. Update `pyproject.toml` to match
3. Re-run build scripts

## Testing Built Applications

### Windows
```bash
# Test installer on clean system
# Run installer and verify:
# - Application launches correctly
# - All features work (connection, plugins, etc.)
# - Uninstaller removes all files
```

### macOS
```bash
# Test on both Intel and Apple Silicon if possible
# Verify:
# - Application launches without console
# - Gatekeeper accepts the app (if code signed)
# - All features work correctly
```

### Linux
```bash
# Test on multiple distributions
# Verify:
# - Desktop entry works
# - All dependencies are satisfied
# - Application functions correctly
```

## Troubleshooting

### Windows Build Issues
- **InnoSetup not found**: Install InnoSetup and add to PATH
- **Missing dependencies**: Ensure all requirements are installed
- **Permission errors**: Run as administrator
- **Python path issues**: Check embedded Python runtime path

### macOS Build Issues
- **PyInstaller fails**: Check for missing hidden imports
- **Editable install fails**: Upgrade tooling, then retry:
  `python3 -m pip install --upgrade pip setuptools wheel`
- **Code signing errors**: Ensure proper certificates installed
- **Notarization failures**: Check entitlements and signing identity
- **`resources/projects.json not found or invalid` at startup**:
  Reinstall from repository root so package data is present:
  `python3 -m pip install --force-reinstall -e .`

### Linux Build Issues
- **Missing system dependencies**: Install development headers
- **Desktop entry not working**: Check paths and permissions
- **Virtual environment issues**: Ensure proper activation

## Advanced Configuration

### Custom Build Options
- **Branding**: Modify icons and splash screens
- **Dependencies**: Add/remove optional dependencies
- **Compression**: Adjust compression settings for installer size
- **Updates**: Configure automatic update mechanisms

### CI/CD Integration
Build scripts can be integrated into GitHub Actions or other CI/CD systems:
```yaml
# Example GitHub Actions workflow
- name: Build Windows Installer
  run: |
    cd setup_tools/inno-win-setup
    ISCC.exe wininstaller.iss

- name: Build macOS DMG
  run: |
    cd setup_tools/mac-os
    ./builddmg.sh
```

## Support

For build-related issues:
1. Check this documentation first
2. Review the main project README.md
3. Search existing GitHub issues
4. Create new issue with build logs and system information

## Contributing

When contributing build improvements:
1. Test on multiple platforms if possible
2. Update documentation for any changes
3. Ensure version synchronization
4. Follow existing code style and patterns