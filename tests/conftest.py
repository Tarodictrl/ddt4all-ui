# tests/conftest.py
from pathlib import Path
import pytest
import sys
import tempfile

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Keep collection away from the developer's real config.json. Test modules and
# ddt4all modules call options.translator() at import time, and translator()
# runs load_configuration() (which would even *create and write* config.json
# when it is missing) before any fixture can redirect anything.
# ddt4all.options has no import-time config access (it only defines
# load_configuration()/save_config()), so importing it here is side-effect free.
# It binds get_config_dir by name (``from ddt4all.file_manager import ...``), so
# the name inside options is patched, before any test module is imported. Then
# load_configuration() is run once against the empty temp dir: it falls back to
# the defaults and writes them there (the file is only ever in the temp dir), so options.configuration holds defaults,
# not the developer's values.
import ddt4all.options as _options  # noqa: E402

_SESSION_CONFIG_DIR = Path(tempfile.mkdtemp(prefix="ddt4all-test-config-"))
_options.get_config_dir = lambda: _SESSION_CONFIG_DIR
_options.load_configuration()
# A fresh config takes the system locale; tests always run with the default
# language. Saved too, because every later translator() call reloads the file.
_options.configuration["lang"] = _options.lang_list["Default"]
_options.save_config()


@pytest.fixture(autouse=True)
def force_english_locale():
    """Force English locale for all tests to ensure consistent output.

    This fixture automatically applies to all tests and ensures that
    translated strings are always in English, preventing test failures
    when the system is configured with different languages (e.g., French).
    """
    # Import and patch all CLI command handlers that use translation
    try:
        import ddt4all.cli.cmd_handlers.doip as doip_module
        doip_module._ = lambda x: x  # Force English for DoIP tests
    except ImportError:
        pass

    # Add more modules here as they start using translation
    # Example:
    # try:
    #     import ddt4all.cli.cmd_handlers.some_module as some_module
    #     some_module._ = lambda x: x
    # except ImportError:
    #     pass


@pytest.fixture(autouse=True)
def isolate_user_config(monkeypatch, tmp_path):
    """Keep tests away from the developer's own config.json.

    Tests read and write the configuration in a temporary folder, and the
    configured ECU database (which may point at a real DDT2000 database) is
    ignored; tests that need a database set the path themselves.
    """
    import ddt4all.options as options
    monkeypatch.setattr(options, "get_config_dir", lambda: tmp_path)
    monkeypatch.setitem(options.configuration, "ecu_database_path", None)


@pytest.fixture
def resources_path():
    return Path(__file__).resolve().parent / "resources"


@pytest.fixture
def dummy_ecu_file(resources_path):
    def _factory(protocol="can", type="json"):
        return resources_path / "chatgpt_generated" / f"dummy_ecu_{protocol}.{type}"
    return _factory
