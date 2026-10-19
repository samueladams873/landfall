from landfall.app import build_window
from landfall.linux.importer import Importer


def test_windows_wizard_builds(window_factory):
    window = window_factory(build_window)
    assert window.windowTitle() == "Landfall Moving Wizard"
    assert window.stack.count() == 7


def test_linux_wizard_builds(window_factory):
    window = window_factory(Importer)
    assert window.stack.count() == 6
    assert window.next_btn.text() == "Get started"


def test_folder_picker_only_leaves_out_what_was_unticked(window_factory, tmp_path):
    from PySide6.QtCore import Qt
    from landfall.ui import FolderPicker
    for d in ("Old backups", "School", "Taxes 2025"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "f.txt").write_text("x")
    (tmp_path / "School" / "g.txt").write_text("y")
    (tmp_path / "Resume.docx").write_text("r")
    picker = FolderPicker(tmp_path, set())
    assert picker.excluded() == set()                      # everything ticked to start
    top = {picker.tree.topLevelItem(i).text(0): picker.tree.topLevelItem(i)
           for i in range(picker.tree.topLevelItemCount())}
    picker.tree.expandItem(top["School"])                  # opening a folder changes nothing
    top["Old backups"].setCheckState(0, Qt.CheckState.Unchecked)
    assert picker.excluded() == {str(tmp_path / "Old backups")}
    school_file = next(top["School"].child(i) for i in range(top["School"].childCount())
                       if top["School"].child(i).text(0) == "f.txt")
    school_file.setCheckState(0, Qt.CheckState.Unchecked)  # one file inside a folder
    assert picker.excluded() == {str(tmp_path / "Old backups"), str(tmp_path / "School" / "f.txt")}
    picker.dialog.deleteLater()
