from PyQt5.QtCore import QObject, QProcess, pyqtSignal


class CommandRunner(QObject):
    """Small wrapper around QProcess that accumulates stdout and emits it
    when the process finishes. Ported from Linux-NitroSense (PyQt6 -> PyQt5)."""

    finished = pyqtSignal(str)  # Emits the full output when done

    def __init__(self):
        super().__init__()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._handle_output)
        self.process.finished.connect(self._on_finished)
        self.output = ""  # Store output here

    def run(self, cmd, args):
        self.output = ""  # Reset output
        self.process.start(cmd, args)
        self.process.waitForFinished()

    def _handle_output(self):
        new_output = bytes(self.process.readAllStandardOutput()).decode()
        self.output += new_output  # Append to stored output

    def _on_finished(self):
        self.finished.emit(self.output)  # Emit the full output

    def close(self):
        self.process.close()
