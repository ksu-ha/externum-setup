import json
import tarfile

from core.state import InstallState
from logging_setup.report import build_report


class FakeLogger:
    def __init__(self, path):
        self.path = path

    def get_directory(self):
        return str(self.path.parent)

    def get_path(self):
        return str(self.path)


def test_report_creation(tmp_path):
    log = tmp_path / "test.log"
    log.write_text("Installation completed", encoding="utf-8")

    logger = FakeLogger(log)
    state = InstallState()

    state.progress.start("Test")
    state.progress.complete()

    # Создаем директорию, куда сохранится отчет
    output_dir = tmp_path / "reports"
    output_dir.mkdir()

    archive_path = build_report(
        state,
        logger,
        output_dir # <--- Передаем папку, а не путь к файлу
    )

    assert archive_path.endswith(".tar.gz")

    with tarfile.open(archive_path, "r:gz") as archive:
        names = archive.getnames()

        assert "report.json" in names
        assert "README.txt" in names
        assert "logs/externum.log" in names

        report = json.load(
            archive.extractfile("report.json")
        )

        assert report["version"] == state.version