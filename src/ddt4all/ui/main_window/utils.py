import errno
from pathlib import Path
import tempfile

import ddt4all.options as options
from ddt4all.ui.theme.theme import apply_theme

_ = options.translator('ddt4all')

BASE_DIR = Path(__file__).resolve().parent

def isWritable(path):
    try:
        testfile = tempfile.TemporaryFile(dir=path)
        testfile.close()
        return True
    except OSError as e:
        if e.errno == errno.EACCES:  # 13
            return False
        e.filename = path
        return False
    except Exception:
        return False

def set_theme_style(app, onoff):
    options.dark_mode = bool(onoff)
    apply_theme(app, options.dark_mode)
    options.configuration["dark"] = options.dark_mode
    options.save_config()


def set_socket_timeout(onoff):
    if (onoff):
        options.configuration["socket_timeout"] = True
    else:
        options.configuration["socket_timeout"] = False

    options.save_config()



