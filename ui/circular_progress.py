from PyQt5.QtCore import (
    Qt, QPropertyAnimation, pyqtProperty, QEasingCurve
)
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
from PyQt5.QtWidgets import QWidget


class CircularProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._value = 0
        self.completed = 0
        self.total = 9

        self.animation = QPropertyAnimation(self, b"value", self)
        self.animation.setDuration(700)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        self.setMinimumSize(180, 180)
        self.setMaximumSize(210, 210)

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = max(0, min(100, int(value)))
        self.update()

    value = pyqtProperty(int, get_value, set_value)

    def set_progress(self, completed, total=9, animate=True):
        self.total = max(1, int(total))
        self.completed = max(0, min(int(completed), self.total))
        target = round(self.completed / self.total * 100)

        self.animation.stop()
        if animate:
            self.animation.setStartValue(self._value)
            self.animation.setEndValue(target)
            self.animation.start()
        else:
            self.set_value(target)

    def reset(self):
        self.animation.stop()
        self.completed = 0
        self.set_value(0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height())
        diameter = side - 24
        x = (self.width() - diameter) / 2
        y = (self.height() - diameter) / 2

        from PyQt5.QtCore import QRectF
        rect = QRectF(x, y, diameter, diameter)

        track = QPen(QColor("#DEDAD0"), 9)
        track.setCapStyle(Qt.RoundCap)
        painter.setPen(track)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(rect, 90 * 16, -360 * 16)

        active = QPen(QColor("#E96A2C"), 9)
        active.setCapStyle(Qt.RoundCap)
        painter.setPen(active)
        painter.drawArc(rect, 90 * 16, -int(360 * self._value / 100 * 16))

        painter.setPen(QColor("#252522"))
        font = QFont("Segoe UI", 29)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            self.rect().adjusted(0, -8, 0, -8),
            Qt.AlignCenter,
            f"{self.completed}/{self.total}"
        )

        painter.setFont(QFont("Consolas", 9))
        painter.setPen(QColor("#77736B"))
        painter.drawText(
            self.rect().adjusted(0, 43, 0, 0),
            Qt.AlignCenter,
            f"{self._value}% ГОТОВО"
        )

        painter.end()