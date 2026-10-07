from PySide6.QtWidgets import QCheckBox, QWidget


class SettingsPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.remember = QCheckBox("Remember me", self)
        self.remember.toggled.connect(self.on_checkbox_toggled)

    def on_checkbox_toggled(self, checked: bool) -> None:
        pass
