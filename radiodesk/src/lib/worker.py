from __future__ import annotations
from typing import Callable, Any
from PySide6.QtCore import QRunnable, QObject, Signal, Slot


class _Signals(QObject):
    result: Signal = Signal(object)
    error: Signal = Signal(str)
    finished: Signal = Signal()


class ApiWorker(QRunnable):
    def __init__(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _Signals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()
