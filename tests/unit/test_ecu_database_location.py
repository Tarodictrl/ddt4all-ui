import json
import zipfile

import pytest

import ddt4all.options as options
from ddt4all.core.ecu.ecu_database import EcuDatabase

ECULIST = """\
<ECUlist>
  <Function Address="38">
    <Target group="UCH" href="test.xml" Name="Test ECU">
      <Protocol>CAN</Protocol>
      <Projects><X95PH2/></Projects>
      <AutoIdents><AutoIdent DiagVersion="01" Supplier="S" Soft="S" Version="1"/></AutoIdents>
    </Target>
  </Function>
</ECUlist>
"""


def _write_zip(path, project="X95PH2"):
    dbdict = {
        "test.json": {
            "group": "UCH", "protocol": "CAN", "projects": [project],
            "address": "26", "ecuname": "Test ECU", "autoidents": [],
        }
    }
    with zipfile.ZipFile(str(path), mode="w") as zf:
        zf.writestr("db.json", json.dumps(dbdict))
    return path


def _write_xml_dir(path):
    path.mkdir(parents=True)
    (path / "eculist.xml").write_text(ECULIST)
    return path


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Empty working directory, no configured database, config never saved."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setitem(options.configuration, "ecu_database_path", None)
    monkeypatch.setattr(options, "save_config", lambda: None)
    return cwd


def test_nothing_found(workdir):
    assert options.get_ecu_zip_path() is None
    assert options.get_ecus_dir() is None
    assert options.get_ecu_database_location() is None


def test_falls_back_to_working_directory(workdir):
    _write_zip(workdir / "ecu.zip")
    _write_xml_dir(workdir / "ecus")
    assert options.get_ecu_zip_path() == "ecu.zip"
    assert options.get_ecus_dir() == "ecus"


def test_configured_zip_wins_over_local(workdir, tmp_path):
    _write_zip(workdir / "ecu.zip")
    (tmp_path / "elsewhere").mkdir()
    other = _write_zip(tmp_path / "elsewhere" / "my db.zip")
    options.set_ecu_database_path(str(other))
    assert options.get_ecu_zip_path() == str(other)
    assert options.get_ecu_database_location() == str(other)


def test_missing_configured_path_falls_back(workdir, tmp_path):
    _write_zip(workdir / "ecu.zip")
    options.set_ecu_database_path(str(tmp_path / "gone.zip"))
    assert options.get_ecu_zip_path() == "ecu.zip"


def test_configured_folder(workdir, tmp_path):
    xml_dir = _write_xml_dir(tmp_path / "ddt2000" / "ecus")
    (tmp_path / "ddt2000" / "graphics").mkdir()
    # Parent folder, the ecus folder and eculist.xml all resolve to the ecus folder
    for picked in (tmp_path / "ddt2000", xml_dir, xml_dir / "eculist.xml"):
        options.set_ecu_database_path(str(picked))
        assert options.get_ecus_dir() == str(xml_dir)
        assert options.get_ecu_zip_path() is None
    assert options.get_graphics_dir() == str(tmp_path / "ddt2000" / "graphics")


def test_normalize_folder_with_zip(tmp_path):
    zpath = _write_zip(tmp_path / "ecu.zip")
    assert options.normalize_ecu_database_path(str(tmp_path)) == ("zip", str(zpath))
    assert options.normalize_ecu_database_path(str(tmp_path / "nope")) == (None, None)
    assert options.normalize_ecu_database_path(None) == (None, None)


def test_database_loads_from_configured_zip(workdir, tmp_path):
    _write_zip(workdir / "ecu.zip", project="LOCAL")
    _write_zip(tmp_path / "picked.zip", project="PICKED")
    options.set_ecu_database_path(str(tmp_path / "picked.zip"))
    assert EcuDatabase().vehiclemap == {"PICKED": [("CAN", "26")]}


def test_database_loads_from_configured_folder(workdir, tmp_path):
    _write_xml_dir(tmp_path / "db")
    options.set_ecu_database_path(str(tmp_path / "db"))
    assert EcuDatabase().vehiclemap == {"X95PH2": [("CAN", "26")]}


def test_corrupt_zip_does_not_crash(workdir, tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip")
    options.set_ecu_database_path(str(bad))
    assert EcuDatabase().numecu == 0
