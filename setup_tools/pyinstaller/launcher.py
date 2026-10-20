"""Entry point of the frozen (PyInstaller) DDT4ALL build.

DDT4ALL looks for its ECU database (``ecu.zip``, ``ecus/``) in the *current
working directory*, so a frozen build must start in a sensible, writable
folder:

* Windows (portable zip): the folder that holds ``DDT4ALL.exe``.
* Linux / macOS (``.deb``, ``.rpm``, AppImage, ``.dmg``): the per-user data
  folder (``platformdirs.user_data_dir("ddt4all")``), created on first run,
  because the install location (``/opt``, a mounted AppImage, an ``.app``
  bundle) is read-only.

``DDT4ALL_HOME`` overrides the choice (handy for tests and power users).
When not frozen (``python launcher.py``) the working directory is untouched.
"""
import os
import sys
from pathlib import Path


def resolve_workdir(platform=None, executable=None, environ=None):
    """Return the working directory a frozen build must start in."""
    platform = sys.platform if platform is None else platform
    executable = sys.executable if executable is None else executable
    environ = os.environ if environ is None else environ

    override = environ.get("DDT4ALL_HOME")
    if override:
        return Path(override).expanduser()
    if platform.startswith("win"):
        return Path(executable).resolve().parent

    from platformdirs import PlatformDirs

    return Path(PlatformDirs("ddt4all").user_data_dir)


def enter_workdir():
    """Create (if needed) and chdir into the frozen build's working folder."""
    workdir = resolve_workdir()
    workdir.mkdir(parents=True, exist_ok=True)
    os.chdir(str(workdir))
    return workdir


def fix_plugins_dir():
    """Point the plugin loader at ``<bundle>/ddt4all/plugins``.

    ``main_widget`` computes ``BASE_DIR / ".." / ".." / "plugins"`` from a
    module living inside the PYZ archive, so the intermediate directories
    (``ddt4all/ui/main_window``) do not exist on disk. Windows resolves ``..``
    lexically and copes, Linux and macOS fail with ENOENT. Use the real folder
    instead.
    """
    import ddt4all
    import ddt4all.ui.main_window.main_widget as main_widget

    main_widget.plugins_base_dir = Path(ddt4all.__file__).resolve().parent / "plugins"


def run():
    if getattr(sys, "frozen", False):
        enter_workdir()
        fix_plugins_dir()

    from ddt4all.main import main

    sys.exit(main())


if __name__ == "__main__":
    run()
