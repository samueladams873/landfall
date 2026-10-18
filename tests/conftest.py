import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    from landfall.ui import make_app
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or make_app([])
    yield app


@pytest.fixture
def window_factory(qapp):
    """Build windows for a test and always destroy them before Qt shuts down."""
    import shiboken6
    made = []

    def make(cls_or_fn):
        w = cls_or_fn()
        made.append(w)
        return w

    yield make
    for w in made:
        for thread, _task in getattr(w, "_tasks", []):
            thread.quit()
            thread.wait(3000)
        w.close()
        shiboken6.delete(w)
    qapp.processEvents()
