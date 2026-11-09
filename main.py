
import sys
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox

from core.state import InstallState
from logging_setup.logger import create_logger
from ui.main_window import MainWindow
from ui.theme import APP_STYLE


def main():
    app = QApplication(sys.argv)

    app.setApplicationName("Externum Setup")
    app.setOrganizationName("Externum")

    logger = create_logger()

    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(
                exc_type,
                exc_value,
                exc_traceback
            )
            return

        details = "".join(
            traceback.format_exception(
                exc_type,
                exc_value,
                exc_traceback
            )
        )

        logger.error(details)

        QMessageBox.critical(
            None,
            "Критическая ошибка",
            "Произошла непредвиденная ошибка.\n"
            "Подробности сохранены в журнале:\n"
            + logger.get_path()
        )

    sys.excepthook = exception_handler

    app.setStyleSheet(APP_STYLE)

    state = InstallState()
    window = MainWindow(state, logger)

    window.show()

    logger.info("Externum Setup started")

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
