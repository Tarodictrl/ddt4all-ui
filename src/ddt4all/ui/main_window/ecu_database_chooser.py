"""Let the user point DDT4ALL at their own ECU database.

The DDT2000 database is not distributed with DDT4ALL. Users pick either a
DDT4ALL zip database (``ecu.zip``) or an extracted XML folder containing
``eculist.xml``; the choice is stored as ``ecu_database_path`` in the
configuration (see :func:`ddt4all.options.get_ecu_zip_path`).
"""
import os
import zipfile

import PyQt5.QtWidgets as widgets

import ddt4all.options as options
import ddt4all.version as version

_ = options.translator('ddt4all')


def describe_ecu_database():
    """Database location shown to the user, or a 'not found' marker."""
    return options.get_ecu_database_location() or _("not found")


def _start_dir():
    location = options.get_ecu_database_location()
    if location:
        return os.path.dirname(os.path.abspath(location))
    return os.getcwd()


def _is_valid_zip(path):
    try:
        with zipfile.ZipFile(path, mode="r") as zf:
            return "db.json" in zf.namelist()
    except (OSError, zipfile.BadZipFile):
        return False


def choose_ecu_database(parent=None, folder=False):
    """Ask for a database zip (or ``eculist.xml``) or, with ``folder``, a folder.

    Saves the choice in the configuration and returns the normalized path,
    or ``None`` when the user cancels or picks something unusable.
    """
    if folder:
        path = widgets.QFileDialog.getExistingDirectory(
            parent, _("Select ECU database folder"), _start_dir())
    else:
        path, _selected = widgets.QFileDialog.getOpenFileName(
            parent, _("Select ECU database"), _start_dir(),
            _("ECU database (*.zip eculist.xml)") + ";;" + _("All files (*)"))
    if not path:
        return None

    kind, normalized = options.normalize_ecu_database_path(path)
    if kind == "zip" and not _is_valid_zip(normalized):
        kind = None
    if not kind:
        widgets.QMessageBox.warning(
            parent, version.__appname__,
            _("No ECU database found at:") + "\n" + path + "\n\n"
            + _("Choose a DDT4ALL 'ecu.zip' file or a folder containing 'eculist.xml'."))
        return None

    options.set_ecu_database_path(normalized)
    return normalized


def make_choose_button(parent, on_chosen):
    """'Choose…' button with a menu: database file or extracted folder.

    ``on_chosen(path)`` is called after a valid database has been saved.
    """
    button = widgets.QPushButton(_("Choose..."), parent)
    menu = widgets.QMenu(button)

    def pick(folder):
        path = choose_ecu_database(parent, folder=folder)
        if path:
            on_chosen(path)

    menu.addAction(_("Database file (ecu.zip)...")).triggered.connect(lambda: pick(False))
    menu.addAction(_("Extracted folder (eculist.xml)...")).triggered.connect(lambda: pick(True))
    button.setMenu(menu)
    return button


def build_database_prompt(parent=None):
    """Build the 'No database found' box; returns ``(box, file_btn, folder_btn)``."""
    msgbox = widgets.QMessageBox(parent)
    msgbox.setWindowTitle(version.__appname__)
    msgbox.setIcon(widgets.QMessageBox.Warning)
    msgbox.setText(_("No database found"))
    msgbox.setInformativeText(
        _("DDT4ALL does not include the ECU database. Choose your 'ecu.zip' "
          "file or a folder containing 'eculist.xml'."))
    file_button = msgbox.addButton(_("Choose file..."), widgets.QMessageBox.AcceptRole)
    folder_button = msgbox.addButton(_("Choose folder..."), widgets.QMessageBox.AcceptRole)
    msgbox.addButton(_("Close"), widgets.QMessageBox.RejectRole)
    msgbox.setDefaultButton(file_button)
    return msgbox, file_button, folder_button


def ask_for_database(parent=None):
    """'No database found' prompt offering to choose one.

    Returns the chosen path, or ``None`` if the user closed the prompt.
    """
    msgbox, file_button, folder_button = build_database_prompt(parent)
    msgbox.exec_()

    clicked = msgbox.clickedButton()
    if clicked is file_button:
        return choose_ecu_database(parent, folder=False)
    if clicked is folder_button:
        return choose_ecu_database(parent, folder=True)
    return None
