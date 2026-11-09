
from core.progress import ProgressState


def test_progress_start():
    state = ProgressState()

    state.start("Проверка")

    assert state.status == "running"
    assert state.percent is None


def test_progress_update():
    state = ProgressState()

    state.start("Установка")
    state.update("Подготовка", 40)

    assert state.percent == 40
    assert state.operation == "Подготовка"


def test_unknown_progress():
    state = ProgressState()

    state.start("Установка")
    state.update("Выполнение процесса")

    assert state.percent is None


def test_progress_complete():
    state = ProgressState()

    state.start("Установка")
    state.complete()

    assert state.status == "success"
    assert state.percent == 100


def test_progress_error():
    state = ProgressState()

    state.start("Установка")
    state.error("Ошибка")

    assert state.status == "failed"
    assert len(state.errors) == 1
