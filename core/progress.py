
import time


class ProgressState:
    """
    Единое состояние выполнения операции Externum.

    Поддерживает:
    - текущий этап;
    - процент выполнения;
    - неизвестный процент;
    - время выполнения;
    - успешное завершение;
    - ошибки;
    - отмену операции.
    """

    def __init__(self):
        self.status = "idle"
        self.operation = "Ожидание"
        self.percent = None

        self.started_at = None
        self.finished_at = None

        self.errors = []
        self.message = ""

    def start(self, operation="Выполнение"):
        self.status = "running"
        self.operation = operation
        self.percent = None

        self.started_at = time.time()
        self.finished_at = None

        self.errors = []
        self.message = ""

    def update(self, operation=None, percent=None):
        if self.status != "running":
            return

        if operation:
            self.operation = str(operation)

        if percent is not None:
            self.percent = max(
                0,
                min(100, int(percent))
            )
        else:
            self.percent = None

    def complete(self, message="Операция успешно завершена"):
        self.status = "success"
        self.percent = 100
        self.operation = "Завершено"
        self.message = str(message)
        self.finished_at = time.time()

    def error(self, message):
        self.status = "failed"
        self.operation = "Ошибка"
        self.message = str(message)

        self.errors.append(str(message))
        self.finished_at = time.time()

    def cancel(self, message="Операция отменена"):
        self.status = "cancelled"
        self.operation = "Отменено"
        self.message = str(message)
        self.finished_at = time.time()

    @property
    def elapsed_seconds(self):
        if self.started_at is None:
            return 0

        end = (
            self.finished_at
            if self.finished_at is not None
            else time.time()
        )

        return max(0, int(end - self.started_at))

    @property
    def elapsed_text(self):
        seconds = self.elapsed_seconds

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def snapshot(self):
        return {
            "status": self.status,
            "operation": self.operation,
            "percent": self.percent,
            "elapsed_seconds": self.elapsed_seconds,
            "elapsed_text": self.elapsed_text,
            "message": self.message,
            "errors": list(self.errors)
        }
