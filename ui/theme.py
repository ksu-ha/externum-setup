APP_STYLE = """
* {
    font-family: "Segoe UI";
    color: #252522;
}

QMainWindow {
    background: #F3F1EB;
}

QWidget#root {
    background: #F3F1EB;
}

QLabel {
    background: transparent;
}

QLabel#brand {
    font-size: 16px;
    font-weight: 800;
    color: #252522;
}

QLabel#eyebrow {
    font-family: Consolas;
    font-size: 9px;
    letter-spacing: 2px;
    color: #817C72;
}

QLabel#heading {
    font-size: 34px;
    font-weight: 900;
    color: #252522;
}

QLabel#subheading {
    font-size: 13px;
    color: #77736B;
}

QLabel#orange {
    color: #E96A2C;
    font-weight: bold;
}

QLabel#muted {
    color: #817C72;
}

QLabel#checkIcon {
    color: #E96A2C;
    font-size: 31px;
    font-weight: bold;
}

QLabel#checkName {
    font-size: 13px;
    font-weight: 600;
}

QLabel#checkDetail {
    font-family: Consolas;
    font-size: 10px;
    color: #817C72;
}

QLabel#checkStatus {
    font-family: Consolas;
    font-size: 10px;
    font-weight: bold;
}

QFrame#separator {
    background: #D9D5CB;
    border: none;
    max-height: 1px;
}

QFrame#notice {
    background: #252522;
    border: none;
}

/* Стили для карточки PRP */
QFrame#prpCard {
    background: #FAF9F5;
    border: 1px solid #B8B3A8;
    border-left: 4px solid #E96A2C; /* Оранжевая полоска слева */
}

QLabel#prpTitle {
    color: #E96A2C;
    font-family: Consolas;
    font-size: 10px;
    font-weight: bold;
}

QLabel#noticeText {
    color: #F3F1EB;
    font-size: 13px;
}

QPushButton {
    background: #252522;
    color: #FFFFFF;
    border: 1px solid #252522;
    padding: 12px 22px;
    min-height: 20px;
    font-size: 12px;
    font-weight: bold;
}

QPushButton:hover {
    background: #E96A2C;
    border-color: #E96A2C;
    color: #FFFFFF;
}

QPushButton:pressed {
    background: #C94F16;
    border-color: #C94F16;
}

QPushButton:disabled {
    background: #D9D5CB;
    border-color: #D9D5CB;
    color: #817C72;
}

QPushButton#secondary {
    background: transparent;
    color: #252522;
    border: 1px solid #817C72;
}

QPushButton#secondary:hover {
    background: #E96A2C;
    color: #FFFFFF;
    border-color: #E96A2C;
}

/* Кнопка ОТМЕНИТЬ (Оранжевая) */
QPushButton#danger {
    background: #E96A2C;
    border-color: #E96A2C;
    color: white;
}
QPushButton#danger:hover {
    background: #CC5725;
    border-color: #CC5725;
}

QLineEdit, QComboBox {
    background: #FAF9F5;
    border: 1px solid #B8B3A8;
    padding: 10px;
    min-height: 22px;
    selection-background-color: #E96A2C;
}

QLineEdit:focus, QComboBox:focus {
    border: 2px solid #E96A2C;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox QAbstractItemView {
    background: #FAF9F5;
    selection-background-color: #E96A2C;
    selection-color: white;
    border: 1px solid #B8B3A8;
}

QTextEdit, QPlainTextEdit {
    background: #252522;
    color: #D8D5CB;
    border: none;
    padding: 12px;
    font-family: Consolas;
    font-size: 10px;
}

QProgressBar {
    background: #DEDAD0;
    border: none;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background: #E96A2C;
}

QScrollArea {
    border: none;
    background: transparent;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border: 1px solid #817C72;
    background: #FAF9F5;
}

QCheckBox::indicator:checked {
    background: #E96A2C;
    border-color: #E96A2C;
}

QScrollBar:vertical {
    background: transparent;
    width: 7px;
}

QScrollBar::handle:vertical {
    background: #B8B3A8;
    min-height: 24px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QFrame#prpCard {
    background: #FAF9F5;
    border: 1px solid #B8B3A8;
    border-left: 4px solid #E96A2C;
}

QPushButton#danger {
    background: #E96A2C;
    border-color: #E96A2C;
    color: white;
}
QPushButton#danger:hover {
    background: #CC5725;
    border-color: #CC5725;
}
"""
