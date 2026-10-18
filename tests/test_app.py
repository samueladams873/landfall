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
