import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from .security import redact


class InstallWorker(QThread):
    output = pyqtSignal(str)
    progress = pyqtSignal(object)
    finished_result = pyqtSignal(bool, int, str)

    def __init__(self, demo=False, script_path=None, env_extra=None, parent=None):
        super().__init__(parent)
        self.demo = demo
        self.script_path = script_path
        self.env_extra = dict(env_extra or {})
        self._cancel_requested = False
        self.process = None
        self.started_at = None

    def cancel(self):
        self._cancel_requested = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except OSError:
                pass

    def emit_output(self, text):
        self.output.emit(redact(text))

    def run_demo(self):
        steps = [
            ("Проверка конфигурации", 10),
            ("Подготовка каталогов", 25),
            ("Проверка компонентов", 40),
            ("Подготовка сценария", 60),
            ("Имитация выполнения", 80),
            ("Демонстрационное завершение", 100)
        ]

        for operation, percent in steps:
            if self._cancel_requested:
                self.finished_result.emit(False, -1, "Операция отменена")
                return
            self.progress.emit({"operation": operation, "percent": percent})
            self.emit_output(f"[DEMO] {operation}")
            time.sleep(0.65)

        self.finished_result.emit(
            True, 0, "Демонстрация завершена. Системная установка не выполнялась."
        )

    def run_script(self):
        if platform.system() != "Linux":
            self.finished_result.emit(False, -1, "Реальная установка разрешена только в Linux")
            return

        if not self.script_path:
            self.finished_result.emit(False, -1, "Не указан путь к install.sh")
            return

        script = Path(self.script_path).resolve()
        if not script.is_file():
            self.finished_result.emit(False, -1, f"Сценарий не найден: {script}")
            return

        if not os.access(str(script), os.R_OK):
            self.finished_result.emit(False, -1, "Нет прав на чтение сценария")
            return

        if os.geteuid() != 0:
            self.finished_result.emit(False, -1, "Для реального запуска откройте приложение с правами root (sudo)")
            return

        # Собираем аргументы для CLI-режима оригинального install.sh
        # ПАРОЛЬ НЕ ПЕРЕДАЕТСЯ ЧЕРЕЗ ARGV!
        args = ["/bin/bash", str(script), "--mode", "cli"]

        system_type = self.env_extra.get("system_type", "centralized")
        args.extend(["--system-type", system_type])

        project_server = self.env_extra.get("project_server", "")
        if project_server:
            args.extend(["--project-server", project_server])

        history_server = self.env_extra.get("history_server", "")
        if history_server:
            args.extend(["--history-server", history_server])

        ssh_user = self.env_extra.get("ssh_user", "")
        if ssh_user:
            args.extend(["--user", ssh_user])

        # Пароль передаем через stdin, а не в args
        
        ntp_server = self.env_extra.get("ntp_server", "")
        if ntp_server:
            args.extend(["--ntp-server", ntp_server])

        apt_server = self.env_extra.get("apt_server", "")
        if apt_server:
            args.extend(["--apt-server", apt_server])

        apt_iso = self.env_extra.get("apt_iso", "")
        if apt_iso:
            args.extend(["--apt-iso", apt_iso])

        # Передаем пароль через переменную окружения (безопаснее чем argv)
        env = {
            **os.environ,
            "TERM": "dumb",
            "LC_ALL": "C.UTF-8",
            "EXTERNUM_SSH_PASSWORD": self.env_extra.get("ssh_password", ""),
        }

        self.emit_output(f"[INFO] Запуск: {script.name} --mode cli --system-type {system_type}")
        self.emit_output(f"[INFO] Аргументы: {' '.join(args[2:])}")

        try:
            self.process = subprocess.Popen(
                args,
                cwd=str(script.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env
            )

            # Эмуляция прогресса для демо-скриптов (по ключевым словам)
            progress_map = {
                "[STUB] Проверка": 10,
                "[STUB] Этап 1": 20,
                "[STUB] Этап 2": 40,
                "[STUB] Этап 3": 60,
                "[STUB] Этап 4": 80,
                "[STUB] Этап 5": 90,
                "[STUB] Установка успешно": 100
            }

            while True:
                if self._cancel_requested:
                    self.process.terminate()
                    break

                line = self.process.stdout.readline()
                if line:
                    self.emit_output(line.rstrip())
                    
                    percent = None
                    for key, val in progress_map.items():
                        if key in line:
                            percent = val
                            break
                            
                    self.progress.emit({
                        "operation": line.strip()[:160] or "Выполнение...",
                        "percent": percent
                    })

                if self.process.poll() is not None:
                    remaining = self.process.stdout.read()
                    if remaining:
                        for item in remaining.splitlines():
                            self.emit_output(item)
                    break

            return_code = self.process.wait()

            if self._cancel_requested:
                self.finished_result.emit(False, return_code, "Выполнение отменено")
                return

            success = return_code == 0
            self.finished_result.emit(
                success,
                return_code,
                "Сценарий завершился успешно" if success else f"Сценарий завершился с кодом {return_code}"
            )

        except (OSError, subprocess.SubprocessError) as exc:
            self.finished_result.emit(False, -1, redact(str(exc)))

    def run(self):
        self.started_at = time.time()
        if self.demo:
            self.run_demo()
        else:
            self.run_script()