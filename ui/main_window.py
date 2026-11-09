import os
import platform
import shutil
import tempfile
import time
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QComboBox, QLineEdit, QFileDialog, QTextEdit,
    QScrollArea, QProgressBar, QDialog,
    QGraphicsDropShadowEffect
)

from core.checks import run_preflight, readiness_summary
from core.network import validate_network_form, interfaces
from core.executor import InstallWorker
from core.iso import ISOManager, ISOError
from core.progress import ProgressState
from core.usbdisk import UsbDisk, UsbDiskError
from core.config_gen import prepare_workspace, ConfigError
from core.prp import configure_prp, PRPError
from core.iso_repo import configure_iso_repo, ISORepoError
from logging_setup.report import build_report
from ui.circular_progress import CircularProgress


# ============================================================
# КАСТОМНЫЕ ДИАЛОГИ EXTERNUM
# ============================================================

class ExternumDialog(QDialog):
    """
    Универсальное кастомное окно:
    info, warning, error, question, confirm.
    """

    def __init__(
        self,
        title,
        message,
        kind="info",
        parent=None,
        accept_text="ПОНЯТНО",
        reject_text=None
    ):
        super().__init__(parent)

        self.kind = kind

        self.setWindowTitle(title)
        self.setFixedSize(480, 290)
        self.setModal(True)
        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)

        panel = QFrame()
        panel.setObjectName("dialogPanel")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(20, 24, 30, 45))
        panel.setGraphicsEffect(shadow)

        root.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(13)

        eyebrow_text = {
            "info": "EXTERNUM / INFORMATION",
            "warning": "EXTERNUM / ATTENTION",
            "error": "EXTERNUM / ERROR",
            "question": "EXTERNUM / CONFIRMATION",
            "confirm": "EXTERNUM / EXECUTION",
        }.get(kind, "EXTERNUM / SYSTEM")

        eyebrow = QLabel(eyebrow_text)
        eyebrow.setObjectName("dialogEyebrow")
        layout.addWidget(eyebrow)

        title_label = QLabel(title)
        title_label.setObjectName("dialogTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        message_label = QLabel(message)
        message_label.setObjectName("dialogMessage")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        layout.addStretch()

        separator = QFrame()
        separator.setObjectName("dialogSeparator")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch()

        if reject_text:
            self.reject_button = QPushButton(reject_text)
            self.reject_button.setObjectName("dialogSecondary")
            self.reject_button.setCursor(Qt.PointingHandCursor)
            self.reject_button.clicked.connect(self.reject)
            buttons.addWidget(self.reject_button)

        self.accept_button = QPushButton(accept_text)
        self.accept_button.setObjectName("dialogPrimary")
        self.accept_button.setCursor(Qt.PointingHandCursor)
        self.accept_button.clicked.connect(self.accept)
        self.accept_button.setDefault(True)
        buttons.addWidget(self.accept_button)

        layout.addLayout(buttons)

        self.setStyleSheet("""
            QFrame#dialogPanel {
                background-color: #F7F7F5;
                border: 1px solid #E3E3DF;
                border-radius: 14px;
            }

            QLabel#dialogEyebrow {
                color: #E66B32;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 2px;
                background: transparent;
                border: none;
            }

            QLabel#dialogTitle {
                color: #202124;
                font-size: 24px;
                font-weight: 800;
                background: transparent;
                border: none;
            }

            QLabel#dialogMessage {
                color: #62666B;
                font-size: 13px;
                background: transparent;
                border: none;
            }

            QFrame#dialogSeparator {
                background-color: #E3E3DF;
                border: none;
            }

            QPushButton#dialogSecondary {
                background-color: #E9E9E6;
                color: #34373A;
                border: 1px solid #D9D9D4;
                border-radius: 7px;
                padding: 12px 20px;
                font-size: 11px;
                font-weight: 800;
                min-width: 75px;
            }

            QPushButton#dialogSecondary:hover {
                background-color: #DEDEDA;
                border-color: #C9C9C3;
            }

            QPushButton#dialogPrimary {
                background-color: #E66B32;
                color: #FFFFFF;
                border: 1px solid #E66B32;
                border-radius: 7px;
                padding: 12px 20px;
                font-size: 11px;
                font-weight: 800;
                min-width: 105px;
            }

            QPushButton#dialogPrimary:hover {
                background-color: #CC5725;
                border-color: #CC5725;
            }

            QPushButton#dialogPrimary:pressed {
                background-color: #B94B1E;
            }

            QPushButton#dialogSecondary:pressed {
                background-color: #D2D2CD;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = (
                event.globalPos() -
                self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if (
            event.buttons() == Qt.LeftButton
            and hasattr(self, "_drag_position")
        ):
            self.move(
                event.globalPos() - self._drag_position
            )
            event.accept()


class CheckWorker(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, iso_path, usb_disk=""):
        super().__init__()
        self.iso_path = iso_path
        self.usb_disk = usb_disk

    def run(self):
        try:
            self.completed.emit(
                run_preflight(self.iso_path, self.usb_disk)
            )
        except Exception as exc:
            self.failed.emit(str(exc))


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self, state, logger):
        super().__init__()

        self.state = state
        self.logger = logger

        self.iso_manager = ISOManager()
        self.workspace = Path(tempfile.gettempdir()) / "externum_workspace"

        self.check_worker = None
        self.install_worker = None

        self.check_results = []
        self.worker_success = False
        self.worker_exit_code = None

        self.setWindowTitle("EXTERNUM / SETUP")
        self.resize(1120, 780)
        self.setMinimumSize(850, 650)

        self.current_page = 0

        self.root = QWidget()
        self.root.setObjectName("root")
        self.setCentralWidget(self.root)

        self.main_layout = QVBoxLayout(self.root)
        self.main_layout.setContentsMargins(32, 22, 32, 22)
        self.main_layout.setSpacing(16)

        self.build_header()

        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack, 1)

        self.pages = [
            self.intro_page(),
            self.check_page(),
            self.network_page(),
            self.iso_page(),
            self.review_page(),
            self.progress_page(),
            self.result_page()
        ]

        for page in self.pages:
            self.stack.addWidget(page)

        self.build_footer()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_elapsed)

        self.show_page(0)

    # --------------------------------------------------------
    # КАСТОМНЫЕ УВЕДОМЛЕНИЯ
    # --------------------------------------------------------

    def notify(self, title, message, kind="info"):
        dialog = ExternumDialog(
            title=title,
            message=message,
            kind=kind,
            parent=self,
            accept_text="ПОНЯТНО"
        )
        dialog.exec_()

    def confirm(self, title, message, accept_text="ДА"):
        dialog = ExternumDialog(
            title=title,
            message=message,
            kind="confirm",
            parent=self,
            accept_text=accept_text,
            reject_text="НЕТ"
        )
        return dialog.exec_() == QDialog.Accepted

    # --------------------------------------------------------
    # HEADER / FOOTER
    # --------------------------------------------------------

    def build_header(self):
        header = QHBoxLayout()

        brand = QLabel("EXTERNUM")
        brand.setObjectName("brand")

        slash = QLabel(" / ")
        slash.setObjectName("orange")

        suffix = QLabel("SETUP")
        suffix.setObjectName("brand")

        header.addWidget(brand)
        header.addWidget(slash)
        header.addWidget(suffix)

        header.addStretch()

        self.step_label = QLabel("01 / INTRO")
        self.step_label.setObjectName("eyebrow")
        header.addWidget(self.step_label)

        self.main_layout.addLayout(header)

        separator = QFrame()
        separator.setObjectName("separator")
        self.main_layout.addWidget(separator)

    def build_footer(self):
        footer = QHBoxLayout()

        self.footer_info = QLabel(
            "ENGINEERING INSTALLER   /   ASTRA LINUX"
        )
        self.footer_info.setObjectName("eyebrow")

        footer.addWidget(self.footer_info)
        footer.addStretch()

        self.back_btn = QPushButton("← НАЗАД")
        self.back_btn.setObjectName("secondary")
        self.back_btn.clicked.connect(self.go_back)

        self.next_btn = QPushButton("ДАЛЕЕ →")
        self.next_btn.clicked.connect(self.go_next)

        footer.addWidget(self.back_btn)
        footer.addWidget(self.next_btn)

        self.main_layout.addLayout(footer)

    # --------------------------------------------------------
    # COMMON PAGE HELPERS
    # --------------------------------------------------------

    def make_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        return page, layout

    def heading(self, layout, eyebrow, title, subtitle=""):
        label = QLabel(eyebrow)
        label.setObjectName("eyebrow")
        layout.addWidget(label)

        title_label = QLabel(title)
        title_label.setObjectName("heading")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("subheading")
            sub.setWordWrap(True)
            layout.addWidget(sub)

    # --------------------------------------------------------
    # PAGE 1: INTRO
    # --------------------------------------------------------

    def intro_page(self):
        page, layout = self.make_page()

        self.heading(
            layout,
            "INSTALLATION SYSTEM / 01",
            "Система\nразвёртывания.",
            "Графический мастер подготовки и установки комплекса "
            "Externum на Astra Linux."
        )

        layout.addSpacing(20)

        notice = QFrame()
        notice.setObjectName("notice")

        notice_layout = QHBoxLayout(notice)
        notice_layout.setContentsMargins(20, 20, 20, 20)

        notice_text = QVBoxLayout()

        notice_title = QLabel("SYSTEM NOTICE / 001")
        notice_title.setObjectName("noticeTitle")

        notice_body = QLabel(
            "Установка может изменить системные пакеты, "
            "репозитории и конфигурацию узлов."
        )
        notice_body.setObjectName("noticeText")
        notice_body.setWordWrap(True)

        notice_text.addWidget(notice_title)
        notice_text.addWidget(notice_body)

        notice_layout.addLayout(notice_text, 1)
        layout.addWidget(notice)

        layout.addSpacing(15)

        layout.addWidget(QLabel("РЕЖИМ ВЫПОЛНЕНИЯ"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Демонстрационный",
            "Реальная установка"
        ])

        if platform.system() == "Windows":
            self.mode_combo.setCurrentIndex(0)
            self.mode_combo.setEnabled(False)

        layout.addWidget(self.mode_combo)

        layout.addWidget(
            QLabel("ТОПОЛОГИЯ РАЗВЁРТЫВАНИЯ")
        )

        self.topology_combo = QComboBox()
        self.topology_combo.addItems([
            "Единая",
            "Распределённая"
        ])

        layout.addWidget(self.topology_combo)

        layout.addWidget(QLabel("КАТАЛОГ USB-DISK"))

        usb_row = QHBoxLayout()

        self.usb_input = QLineEdit()
        self.usb_input.setPlaceholderText(
            "Например: /home/forpost/usb-disk"
        )
        usb_row.addWidget(self.usb_input, 1)

        usb_browse = QPushButton("ОБЗОР")
        usb_browse.setObjectName("secondary")
        usb_browse.clicked.connect(self.select_usb_disk)
        usb_row.addWidget(usb_browse)

        layout.addLayout(usb_row)

        self.usb_status = QLabel("Каталог usb-disk не указан")
        self.usb_status.setObjectName("checkDetail")
        self.usb_status.setWordWrap(True)
        layout.addWidget(self.usb_status)

        layout.addStretch()

        return page

    def select_usb_disk(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Выбрать каталог usb-disk",
            self.usb_input.text().strip() or ""
        )

        if not path:
            return

        self.usb_input.setText(path)
        self.validate_usb_disk(path)

    def validate_usb_disk(self, path):
        try:
            info = UsbDisk(path).validate()
            self.state.usb_disk = info["root"]
            self.usb_status.setText(
                "OK: install.sh, under-install.sh, "
                "config.yml найдены в usb-disk"
            )
            self.logger.info(
                f"usb-disk selected: {info['root']}"
            )
        except UsbDiskError as exc:
            self.state.usb_disk = ""
            self.usb_status.setText(str(exc))

    # --------------------------------------------------------
    # PAGE 2: CHECKS
    # --------------------------------------------------------

    def check_page(self):
        page, layout = self.make_page()

        self.heading(
            layout,
            "PRE-FLIGHT / SYSTEM DIAGNOSTICS",
            "Готовность системы",
            "Контрольные зоны перед началом развёртывания."
        )

        top = QHBoxLayout()

        self.circular = CircularProgress()
        top.addWidget(self.circular)

        description = QVBoxLayout()

        self.readiness_title = QLabel(
            "Проверка ещё не запускалась"
        )
        self.readiness_title.setObjectName("brand")

        self.readiness_detail = QLabel(
            "Запустите диагностику для оценки готовности."
        )
        self.readiness_detail.setWordWrap(True)
        self.readiness_detail.setObjectName("subheading")

        self.check_btn = QPushButton("ЗАПУСТИТЬ ПРОВЕРКИ")
        self.check_btn.clicked.connect(self.start_checks)

        description.addWidget(self.readiness_title)
        description.addWidget(self.readiness_detail)
        description.addSpacing(12)
        description.addWidget(self.check_btn)
        description.addStretch()

        top.addLayout(description, 1)
        layout.addLayout(top)

        separator = QFrame()
        separator.setObjectName("separator")
        layout.addWidget(separator)

        self.check_container = QWidget()
        self.check_layout = QVBoxLayout(self.check_container)
        self.check_layout.setContentsMargins(0, 0, 0, 0)
        self.check_layout.setSpacing(7)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.check_container)

        layout.addWidget(scroll, 1)

        return page

    def clear_checks(self):
        while self.check_layout.count():
            item = self.check_layout.takeAt(0)
            widget = item.widget()

            if widget:
                widget.deleteLater()

    def render_checks(self, results):
        self.clear_checks()

        for item in results:
            row = QHBoxLayout()

            icon = QLabel("✓" if item["ok"] else "×")
            icon.setObjectName("checkIcon")
            icon.setFixedWidth(36)

            content = QVBoxLayout()

            name = QLabel(item["name"])
            name.setObjectName("checkName")

            detail = QLabel(item["detail"])
            detail.setObjectName("checkDetail")
            detail.setWordWrap(True)

            content.addWidget(name)
            content.addWidget(detail)

            status = QLabel(
                "ПРОЙДЕНО" if item["ok"] else
                "ПРЕДУПРЕЖДЕНИЕ" if item["warning"] else
                "ОШИБКА"
            )
            status.setObjectName("checkStatus")

            row.addWidget(icon)
            row.addLayout(content, 1)
            row.addWidget(status)

            self.check_layout.addLayout(row)

            separator = QFrame()
            separator.setObjectName("separator")
            self.check_layout.addWidget(separator)

    def start_checks(self):
        if self.check_worker and self.check_worker.isRunning():
            return

        if self.usb_input.text().strip():
            self.validate_usb_disk(self.usb_input.text().strip())

        self.check_btn.setEnabled(False)
        self.check_btn.setText("ВЫПОЛНЯЕТСЯ...")

        self.circular.reset()
        self.readiness_title.setText(
            "Выполняется диагностика"
        )

        self.check_worker = CheckWorker(
            self.state.iso_path,
            self.state.usb_disk
        )
        self.check_worker.completed.connect(self.checks_finished)
        self.check_worker.failed.connect(self.checks_failed)
        self.check_worker.start()

    def checks_finished(self, results):
        self.check_results = results
        self.state.check_results = results

        summary = readiness_summary(results)

        self.circular.set_progress(
            summary["passed"],
            summary["total"]
        )

        self.readiness_title.setText(
            "Система готова" if summary["ready"]
            else "Обнаружены замечания"
        )

        self.readiness_detail.setText(
            f"Обязательных проверок пройдено: "
            f"{summary['passed']} из {summary['total']}. "
            f"Предупреждений: {len(summary['warnings'])}."
        )

        self.render_checks(results)

        self.check_btn.setEnabled(True)
        self.check_btn.setText("ПОВТОРИТЬ ПРОВЕРКИ")

        self.logger.info(
            f"Preflight completed: "
            f"{summary['passed']}/{summary['total']}"
        )

    def checks_failed(self, message):
        self.logger.error(message)

        self.readiness_title.setText("Ошибка диагностики")
        self.readiness_detail.setText(message)

        self.check_btn.setEnabled(True)
        self.check_btn.setText("ПОВТОРИТЬ ПРОВЕРКИ")

        self.notify(
            "Ошибка диагностики",
            message,
            "error"
        )

    # --------------------------------------------------------
    # PAGE 3: NETWORK
    # --------------------------------------------------------

    def network_page(self):
        page, layout = self.make_page()

        self.heading(
            layout,
            "NETWORK / CONFIGURATION",
            "Сетевая конфигурация",
            "Укажите параметры сети целевого узла. "
            "Серые значения — примеры формата, а не настройки по умолчанию."
        )

        layout.addSpacing(15)

        layout.addWidget(QLabel("СЕТЕВОЙ ИНТЕРФЕЙС"))

        self.interface_combo = QComboBox()
        found = interfaces()

        if found:
            self.interface_combo.addItems(found)
        else:
            self.interface_combo.addItem("eth0")

        layout.addWidget(self.interface_combo)

        # --- PRP card (появляется только при >= 2 интерфейсах) ---

        self.prp_card = QFrame()
        self.prp_card.setObjectName("prpCard")
        prp_layout = QVBoxLayout(self.prp_card)
        prp_layout.setContentsMargins(16, 14, 16, 14)
        prp_layout.setSpacing(8)

        prp_title = QLabel("PRP / ОТКАЗОУСТОЙЧИВЫЙ ИНТЕРФЕЙС")
        prp_title.setObjectName("noticeTitle")

        self.prp_hint = QLabel(
            "Обнаружено несколько интерфейсов. "
            "Рекомендуется выделить отдельный PRP-интерфейс "
            "для стабильной работы системы."
        )
        self.prp_hint.setObjectName("subheading")
        self.prp_hint.setWordWrap(True)

        prp_row = QHBoxLayout()

        self.prp_combo = QComboBox()
        self.prp_combo.addItems(found or ["eth0"])
        prp_row.addWidget(self.prp_combo, 1)

        self.prp_enable_btn = QPushButton("ВКЛЮЧИТЬ PRP")
        self.prp_enable_btn.setObjectName("secondary")
        self.prp_enable_btn.clicked.connect(self.enable_prp)
        prp_row.addWidget(self.prp_enable_btn)

        self.prp_skip_btn = QPushButton("БЕЗ PRP")
        self.prp_skip_btn.setObjectName("secondary")
        self.prp_skip_btn.clicked.connect(self.skip_prp)
        prp_row.addWidget(self.prp_skip_btn)

        prp_layout.addWidget(prp_title)
        prp_layout.addWidget(self.prp_hint)
        prp_layout.addLayout(prp_row)

        self.prp_status = QLabel("PRP не настроен")
        self.prp_status.setObjectName("checkDetail")
        self.prp_status.setWordWrap(True)
        prp_layout.addWidget(self.prp_status)

        layout.addWidget(self.prp_card)

        self.prp_card.setVisible(len(found) >= 2)

        # --- Основные поля ---

        fields = [
            ("IP-АДРЕС", "ip", "Например: 192.168.1.10"),
            ("МАСКА CIDR", "cidr", "Например: 24"),
            ("ШЛЮЗ", "gateway", "Например: 192.168.1.1"),
            ("DNS", "dns", "Например: 8.8.8.8"),
        ]

        self.network_inputs = {}

        for label, key, placeholder in fields:
            layout.addWidget(QLabel(label))

            field = QLineEdit()
            field.setPlaceholderText(placeholder)

            self.network_inputs[key] = field
            layout.addWidget(field)

        self.network_error = QLabel("")
        self.network_error.setStyleSheet("color: #B83225;")
        self.network_error.setWordWrap(True)

        layout.addWidget(self.network_error)
        layout.addStretch()

        return page

    def enable_prp(self):
        if not self.state.usb_disk:
            self.notify(
                "usb-disk не выбран",
                "Укажите каталог usb-disk на первом экране.",
                "warning"
            )
            return

        iface = self.prp_combo.currentText()
        ip = self.network_inputs["ip"].text().strip()

        if platform.system() != "Linux":
            self.state.prp_enabled = True
            self.state.prp_interface = iface
            self.prp_status.setText(
                f"Демо-режим: PRP отмечен на {iface} "
                f"({ip or 'без IP'})"
            )
            self.logger.info(f"PRP enabled (demo) on {iface}")
            return

        if not ip:
            self.notify(
                "IP не задан",
                "Сначала укажите IP-адрес для PRP.",
                "warning"
            )
            return

        try:
            output = configure_prp(
                self.state.usb_disk,
                iface,
                ip
            )
            self.state.prp_enabled = True
            self.state.prp_interface = iface
            self.prp_status.setText(
                f"PRP настроен на {iface}: "
                f"{output[-200:] or 'OK'}"
            )
            self.logger.info(f"PRP configured on {iface}")

        except PRPError as exc:
            self.logger.error(str(exc))
            self.notify("Ошибка PRP", str(exc), "error")

    def skip_prp(self):
        self.state.prp_enabled = False
        self.state.prp_interface = ""
        self.prp_status.setText(
            "Продолжаем без PRP (рекомендуется настроить)"
        )
        self.logger.info("PRP skipped by user")

    # --------------------------------------------------------
    # PAGE 4: ISO
    # --------------------------------------------------------

    def iso_page(self):
        page, layout = self.make_page()

        self.heading(
            layout,
            "SOURCE / ISO IMAGE",
            "Источник установки",
            "Выберите образ с компонентами Externum."
        )

        layout.addSpacing(20)

        self.iso_path_label = QLabel("ISO НЕ ВЫБРАН")
        self.iso_path_label.setObjectName("eyebrow")
        self.iso_path_label.setWordWrap(True)

        layout.addWidget(self.iso_path_label)

        self.iso_info = QLabel(
            "Выберите ISO-файл для проверки."
        )
        self.iso_info.setObjectName("subheading")
        self.iso_info.setWordWrap(True)

        layout.addWidget(self.iso_info)

        browse = QPushButton("ВЫБРАТЬ ISO")
        browse.clicked.connect(self.select_iso)
        layout.addWidget(browse)

        self.mount_button = QPushButton(
            "СМОНТИРОВАТЬ ISO (RO)"
        )
        self.mount_button.setObjectName("secondary")
        self.mount_button.clicked.connect(self.mount_iso)

        self.unmount_button = QPushButton(
            "РАЗМОНТИРОВАТЬ ISO"
        )
        self.unmount_button.setObjectName("secondary")
        self.unmount_button.clicked.connect(self.unmount_iso)

        layout.addWidget(self.mount_button)
        layout.addWidget(self.unmount_button)

        self.iso_repo_button = QPushButton(
            "ПОДКЛЮЧИТЬ ISO КАК РЕПОЗИТОРИЙ"
        )
        self.iso_repo_button.setObjectName("secondary")
        self.iso_repo_button.clicked.connect(self.setup_iso_repo)
        layout.addWidget(self.iso_repo_button)

        self.iso_repo_status = QLabel("")
        self.iso_repo_status.setObjectName("checkDetail")
        self.iso_repo_status.setWordWrap(True)
        layout.addWidget(self.iso_repo_status)

        layout.addStretch()

        return page

    def select_iso(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать ISO",
            "",
            "ISO Images (*.iso)"
        )

        if not path:
            return

        try:
            info = self.iso_manager.inspect(path)

            self.state.iso_path = info["path"]
            self.iso_path_label.setText(info["name"])

            size = info["size"] / (1024 ** 3)

            self.iso_info.setText(
                f"ISO 9660 подтверждён. Размер: {size:.2f} ГБ."
            )

            self.logger.info("ISO selected and inspected")

        except ISOError as exc:
            self.notify(
                "Ошибка ISO",
                str(exc),
                "error"
            )

    def mount_iso(self):
        if not self.state.iso_path:
            self.notify(
                "Источник не выбран",
                "Сначала выберите ISO-файл.",
                "warning"
            )
            return

        try:
            path = self.iso_manager.mount(
                self.state.iso_path
            )

            self.iso_info.setText(
                f"Смонтировано только для чтения: {path}"
            )

            self.logger.info("ISO mounted read-only")

        except ISOError as exc:
            self.logger.error(str(exc))

            self.notify(
                "Ошибка монтирования",
                str(exc),
                "error"
            )

    def unmount_iso(self):
        try:
            self.iso_manager.unmount()

            self.iso_info.setText("ISO размонтирован.")
            self.state.iso_repo_ready = False
            self.iso_repo_status.setText("")
            self.logger.info("ISO unmounted")

        except ISOError as exc:
            self.notify(
                "Ошибка размонтирования",
                str(exc),
                "error"
            )

    def setup_iso_repo(self):
        if not self.state.iso_path:
            self.notify(
                "Источник не выбран",
                "Сначала выберите ISO-файл.",
                "warning"
            )
            return

        if not self.state.usb_disk:
            self.notify(
                "usb-disk не выбран",
                "Укажите каталог usb-disk на первом экране.",
                "warning"
            )
            return

        if platform.system() != "Linux":
            self.state.iso_repo_ready = True
            self.iso_repo_status.setText(
                "Демо-режим: ISO-репозиторий отмечен как подключённый"
            )
            self.logger.info("ISO repo enabled (demo)")
            return

        try:
            output = configure_iso_repo(
                self.state.usb_disk,
                self.state.iso_path
            )
            self.state.iso_repo_ready = True
            self.iso_repo_status.setText(
                f"ISO подключён как репозиторий: "
                f"{output[-200:] or 'OK'}"
            )
            self.logger.info("ISO repo configured")

        except ISORepoError as exc:
            self.logger.error(str(exc))
            self.notify(
                "Ошибка ISO-репозитория",
                str(exc),
                "error"
            )

    # --------------------------------------------------------
    # PAGE 5: REVIEW
    # --------------------------------------------------------

    def review_page(self):
        page, layout = self.make_page()

        self.heading(
            layout,
            "FINAL REVIEW / CONFIGURATION",
            "Проверка конфигурации",
            "Перед запуском проверьте выбранные параметры."
        )

        self.review_text = QLabel("")
        self.review_text.setWordWrap(True)
        layout.addWidget(self.review_text)

        self.confirm_label = QLabel(
            "Параметры будут использованы для выполнения установки."
        )
        self.confirm_label.setObjectName("subheading")
        layout.addWidget(self.confirm_label)

        layout.addStretch()

        return page

    # --------------------------------------------------------
    # PAGE 6: EXECUTION
    # --------------------------------------------------------

    def progress_page(self):
        page, layout = self.make_page()

        self.heading(
            layout,
            "EXECUTION / LIVE MONITORING",
            "Выполнение операции",
            "Отслеживание процесса и сообщений установщика."
        )

        self.progress_title = QLabel("Ожидание запуска")
        self.progress_title.setObjectName("brand")
        layout.addWidget(self.progress_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        self.progress_percent = QLabel(
            "ПРОГРЕСС НЕ ОПРЕДЕЛЁН"
        )
        self.progress_percent.setObjectName("eyebrow")
        layout.addWidget(self.progress_percent)

        self.elapsed_label = QLabel("00:00:00")
        self.elapsed_label.setObjectName("eyebrow")
        layout.addWidget(self.elapsed_label)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)

        self.retry_button = QPushButton("ПОВТОРИТЬ")
        self.retry_button.clicked.connect(self.start_install)
        self.retry_button.hide()
        layout.addWidget(self.retry_button)

        self.cancel_button = QPushButton("ОТМЕНИТЬ")
        self.cancel_button.setObjectName("danger")
        self.cancel_button.clicked.connect(self.cancel_install)
        layout.addWidget(self.cancel_button)

        return page

    # --------------------------------------------------------
    # PAGE 7: RESULT
    # --------------------------------------------------------

    def result_page(self):
        page, layout = self.make_page()

        self.heading(
            layout,
            "INSTALLATION / FINAL STATUS",
            "Результат выполнения",
            "Сводка завершённой операции."
        )

        self.result_title = QLabel("Ожидание результата")
        self.result_title.setObjectName("brand")
        layout.addWidget(self.result_title)

        self.result_details = QLabel("")
        self.result_details.setWordWrap(True)
        layout.addWidget(self.result_details)

        self.report_path_label = QLabel("")
        self.report_path_label.setObjectName("checkDetail")
        self.report_path_label.setWordWrap(True)
        layout.addWidget(self.report_path_label)

        self.export_button = QPushButton(
            "СОЗДАТЬ ОТЧЁТ TAR.GZ"
        )
        self.export_button.clicked.connect(self.export_report)
        layout.addWidget(self.export_button)

        self.result_retry_button = QPushButton(
            "ПОВТОРИТЬ ОПЕРАЦИЮ"
        )
        self.result_retry_button.clicked.connect(
            self.retry_install
        )
        layout.addWidget(self.result_retry_button)

        layout.addStretch()

        return page

    # --------------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------------

    def show_page(self, index):
        index = max(0, min(index, len(self.pages) - 1))

        self.current_page = index
        self.stack.setCurrentIndex(index)

        names = [
            "INTRO",
            "PREFLIGHT",
            "NETWORK",
            "ISO",
            "REVIEW",
            "EXECUTION",
            "RESULT"
        ]

        self.step_label.setText(
            f"{index + 1:02d} / {names[index]}"
        )

        self.back_btn.show()
        self.next_btn.show()

        self.back_btn.setEnabled(True)
        self.next_btn.setEnabled(True)
        self.next_btn.setText("ДАЛЕЕ →")

        if index == 0:
            self.back_btn.setEnabled(False)

        elif index == 5:
            self.back_btn.hide()

            finished = (
                self.worker_success
                or self.worker_exit_code is not None
            )

            if finished:
                self.next_btn.setText("К РЕЗУЛЬТАТУ →")
                self.next_btn.show()
            else:
                self.next_btn.hide()

        elif index == 6:
            self.next_btn.hide()

        if index == 4:
            self.update_review()

    def update_review(self):
        self.state.mode = self.topology_combo.currentText()
        self.state.system_type = (
            "centralized"
            if self.state.mode == "Единая"
            else "distributed"
        )
        self.state.run_mode = self.mode_combo.currentText()

        network = {
            key: field.text().strip()
            for key, field in self.network_inputs.items()
        }

        network["interface"] = self.interface_combo.currentText()
        self.state.network = network

        prp_line = (
            f"включён на {self.state.prp_interface}"
            if self.state.prp_enabled
            else "выключен"
        )

        self.review_text.setText(
            f"Режим: {self.state.run_mode}\n\n"
            f"Топология: {self.state.mode} "
            f"({self.state.system_type})\n\n"
            f"Интерфейс: {network['interface']}\n"
            f"IP: {network['ip'] or 'Не задан'}\n"
            f"CIDR: {network['cidr'] or 'Не задан'}\n"
            f"Шлюз: {network['gateway'] or 'Не задан'}\n"
            f"DNS: {network['dns'] or 'Не задан'}\n\n"
            f"PRP: {prp_line}\n"
            f"ISO: {self.state.iso_path or 'Не выбран'}\n"
            f"ISO-репозиторий: "
            f"{'готов' if self.state.iso_repo_ready else 'не готов'}\n"
            f"usb-disk: {self.state.usb_disk or 'Не выбран'}\n"
            f"config.yml: "
            f"{'сгенерирован' if self.state.config_yml else 'нет'}\n"
            f"inventory.yml: "
            f"{'сгенерирован' if self.state.inventory_yml else 'нет'}"
        )

    def go_back(self):
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def go_next(self):
        page = self.current_page

        # Экран выполнения: перейти к результату можно
        # только после завершения операции.
        if page == 5:
            finished = (
                self.worker_success
                or self.worker_exit_code is not None
            )

            if finished:
                self.show_page(6)

            return

        if page == 6:
            return

        self.state.run_mode = self.mode_combo.currentText()
        self.state.mode = self.topology_combo.currentText()
        self.state.system_type = (
            "centralized"
            if self.state.mode == "Единая"
            else "distributed"
        )

        # Диагностика должна быть запущена.
        if page == 1:
            if not self.check_results:
                self.notify(
                    "Проверка не запускалась",
                    "Сначала запустите системную диагностику.",
                    "warning"
                )
                return

        # Проверка сети для реальной установки.
        if page == 2:
            if self.state.run_mode == "Реальная установка":
                data = {
                    key: field.text().strip()
                    for key, field in self.network_inputs.items()
                }

                data["interface"] = self.interface_combo.currentText()

                errors = validate_network_form(data)

                if errors:
                    self.network_error.setText(
                        "\n".join(
                            f"{key}: {value}"
                            for key, value in errors.items()
                        )
                    )

                    self.notify(
                        "Проверьте сеть",
                        "\n".join(
                            f"{key}: {value}"
                            for key, value in errors.items()
                        ),
                        "warning"
                    )
                    return

                self.network_error.clear()
                self.state.network = data
            else:
                self.network_error.clear()

        # Проверка ISO и usb-disk для реальной установки.
        if page == 3:
            if self.state.run_mode == "Реальная установка":
                if platform.system() != "Linux":
                    self.notify(
                        "Недоступный режим",
                        "Реальная установка доступна только в Linux.",
                        "warning"
                    )
                    return

                if not self.state.usb_disk:
                    self.notify(
                        "usb-disk не выбран",
                        "Вернитесь на первый экран и укажите usb-disk.",
                        "warning"
                    )
                    return

                if not self.state.iso_path:
                    self.notify(
                        "Источник не выбран",
                        "Выберите ISO-файл перед продолжением.",
                        "warning"
                    )
                    return

        # Подготовка config.yml и inventory.yml + подтверждение.
        if page == 4:
            if self.state.usb_disk:
                try:
                    paths = prepare_workspace(
                        self.state,
                        self.state.usb_disk,
                        self.workspace
                    )
                    self.state.inventory_yml = paths["inventory"]
                    self.state.config_yml = paths["config"]
                    self.logger.info(
                        "inventory.yml and config.yml prepared"
                    )
                except ConfigError as exc:
                    self.logger.error(str(exc))
                    self.notify(
                        "Ошибка подготовки конфигурации",
                        str(exc),
                        "error"
                    )
                    return

            accepted = self.confirm(
                "Запустить операцию?",
                "Будет запущен процесс развёртывания Externum "
                "с выбранными параметрами конфигурации.\n\n"
                "Перед продолжением убедитесь, что параметры "
                "указаны верно.",
                "ДА, ЗАПУСТИТЬ"
            )

            if not accepted:
                return

            self.worker_success = False
            self.worker_exit_code = None

            self.show_page(5)
            self.start_install()
            return

        self.show_page(page + 1)

    # --------------------------------------------------------
    # INSTALLATION
    # --------------------------------------------------------

    def start_install(self):
        if self.install_worker and self.install_worker.isRunning():
            return

        self.worker_success = False
        self.worker_exit_code = None

        demo = (
            self.state.run_mode == "Демонстрационный"
            or platform.system() == "Windows"
        )

        if self.state.usb_disk:
            default_script = (
                Path(self.state.usb_disk) / "install.sh"
            )
        else:
            default_script = Path.cwd() / "install.sh"

        script_path = os.environ.get(
            "EXTERNUM_INSTALL_SCRIPT",
            str(default_script)
        )

        if not demo and not Path(script_path).is_file():
            self.notify(
                "Установщик не найден",
                "Не найден install.sh. "
                "Укажите путь через EXTERNUM_INSTALL_SCRIPT "
                "или выберите usb-disk на первом экране.",
                "error"
            )
            self.show_page(4)
            return

        self.state.progress = ProgressState()
        self.state.progress.start("Установка")

        self.state.current_stage = "Установка"
        self.state.started_at = time.time()
        self.state.finished_at = None
        self.state.last_error = ""

        self.log_view.clear()
        self.progress_bar.setRange(0, 0)
        self.progress_percent.setText(
            "ПРОГРЕСС НЕ ОПРЕДЕЛЁН"
        )
        self.progress_title.setText("Подготовка...")
        self.elapsed_label.setText("00:00:00")

        self.retry_button.hide()
        self.cancel_button.show()

        self.retry_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

        env_extra = {
            "EXTERNUM_NONINTERACTIVE": "1",
            "EXTERNUM_INVENTORY": self.state.inventory_yml or "",
            "EXTERNUM_CONFIG": self.state.config_yml or "",
            "EXTERNUM_SYSTEM_TYPE": self.state.system_type,
            "EXTERNUM_PRP": "1" if self.state.prp_enabled else "0",
            "EXTERNUM_ISO_REPO": (
                "1" if self.state.iso_repo_ready else "0"
            ),
        }

        self.install_worker = InstallWorker(
            demo=demo,
            script_path=script_path,
            env_extra=env_extra
        )

        self.install_worker.output.connect(self.append_log)
        self.install_worker.progress.connect(self.update_progress)
        self.install_worker.finished_result.connect(
            self.install_finished
        )

        self.install_worker.start()
        self.timer.start(1000)

        self.logger.info(
            "Installation worker started; demo=%s" % demo
        )

    def append_log(self, message):
        self.log_view.append(message)
        self.logger.info(message)

    def update_progress(self, data):
        operation = data.get("operation", "Выполнение")
        self.progress_title.setText(operation)

        percent = data.get("percent")

        if percent is None:
            self.progress_bar.setRange(0, 0)
            self.progress_percent.setText(
                "ПРОГРЕСС НЕ ОПРЕДЕЛЁН"
            )
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percent)
            self.progress_percent.setText(f"{percent}%")

        self.state.progress.update(operation, percent)

    def update_elapsed(self):
        self.elapsed_label.setText(
            self.state.progress.elapsed_text
        )

    def cancel_install(self):
        if not (
            self.install_worker
            and self.install_worker.isRunning()
        ):
            return

        accepted = self.confirm(
            "Остановить операцию?",
            "Вы действительно хотите прервать текущий процесс "
            "развёртывания?",
            "ДА, ОСТАНОВИТЬ"
        )

        if accepted:
            self.install_worker.cancel()
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText("ОСТАНОВКА...")

    def install_finished(self, success, exit_code, message):
        self.timer.stop()

        self.worker_success = success
        self.worker_exit_code = exit_code

        self.state.finished_at = time.time()

        if success:
            self.state.progress.complete(message)
            self.state.current_stage = "Завершено"
            self.result_title.setText("Операция завершена")
        else:
            self.state.progress.error(message)
            self.state.current_stage = "Ошибка"
            self.state.last_error = message
            self.result_title.setText("Обнаружена ошибка")

        self.cancel_button.hide()
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText("ОТМЕНИТЬ")

        self.retry_button.setVisible(not success)

        self.result_details.setText(
            f"Статус: {'УСПЕХ' if success else 'ОШИБКА'}\n"
            f"Код завершения: {exit_code}\n"
            f"Время: {self.state.progress.elapsed_text}\n"
            f"Сообщение: {message}"
        )

        self.logger.info(
            f"Worker finished: success={success}, code={exit_code}"
        )

        self.show_page(6)

    def retry_install(self):
        self.worker_success = False
        self.worker_exit_code = None
        self.show_page(5)
        self.start_install()

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    def export_report(self):
        try:
            path = build_report(
                self.state,
                self.logger
            )

            self.report_path_label.setText(
                f"Отчёт сохранён:\n{path}"
            )

            self.logger.info("Diagnostic report created")

            self.notify(
                "Отчёт создан",
                f"Диагностический отчёт успешно сохранён:\n{path}",
                "info"
            )

        except Exception as exc:
            self.logger.error(str(exc))

            self.notify(
                "Ошибка создания отчёта",
                str(exc),
                "error"
            )

    # --------------------------------------------------------
    # CLOSE
    # --------------------------------------------------------

    def closeEvent(self, event):
        if (
            self.install_worker
            and self.install_worker.isRunning()
        ):
            accepted = self.confirm(
                "Операция выполняется",
                "Установщик ещё работает. "
                "Закрытие приложения может прервать процесс.\n\n"
                "Вы уверены, что хотите закрыть окно?",
                "ЗАКРЫТЬ"
            )

            if not accepted:
                event.ignore()
                return

            self.install_worker.cancel()
            event.ignore()

            self.notify(
                "Остановка процесса",
                "Отправлен запрос на остановку. "
                "Дождитесь завершения операции перед закрытием.",
                "warning"
            )
            return

        try:
            self.iso_manager.close()
        except Exception as exc:
            self.logger.error(str(exc))

        try:
            shutil.rmtree(self.workspace, ignore_errors=True)
        except Exception:
            pass

        event.accept()