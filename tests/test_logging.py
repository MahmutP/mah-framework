import io
import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from core import console as console_module
from core import logger as logger_module
from core.console import Console


class TestLogCleanup(unittest.TestCase):
    """Log dosyaları diski şişirmemeli: retention + toplam boyut limiti."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.log_dir = Path(self._tmp.name)
        self.active = self.log_dir / "app.log"
        self._patchers = [
            patch.object(logger_module, "LOG_DIR", self.log_dir),
            patch.object(logger_module, "LOG_FILE", self.active),
        ]
        for patcher in self._patchers:
            patcher.start()

    def tearDown(self):
        for patcher in self._patchers:
            patcher.stop()
        self._tmp.cleanup()

    def _write(self, name: str, size: int) -> Path:
        path = self.log_dir / name
        path.write_bytes(b"x" * size)
        return path

    def test_removes_old_rotated_logs(self):
        """Retention süresini aşan döndürülmüş loglar silinmeli."""
        old = self._write("app.2020-01-01_00-00-00_000000.log", 1024)
        old_time = time.time() - 30 * 86400
        os.utime(old, (old_time, old_time))
        fresh = self._write("app.2026-01-01_00-00-00_000000.log", 1024)

        removed = logger_module.cleanup_logs(
            retention_days=7, max_total_bytes=10 * 1024 * 1024
        )

        self.assertEqual(removed, 1)
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists())

    def test_enforces_total_size_limit(self):
        """Toplam log boyutu limiti aşınca en eski dosyalar silinmeli."""
        self._write("app.log", 0)
        for index in (1, 2, 3):
            self._write(f"app.2026-01-0{index}_00-00-00_{index:06d}.log", 4 * 1024 * 1024)

        limit = 5 * 1024 * 1024
        removed = logger_module.cleanup_logs(
            retention_days=7, max_total_bytes=limit
        )

        total = sum(path.stat().st_size for path in self.log_dir.glob("app*.log*"))
        self.assertGreater(removed, 0)
        self.assertLessEqual(total, limit)

    def test_truncates_oversized_active_log(self):
        """Aktif app.log tek başına limiti aşıyorsa sıfırlanmalı."""
        active = self._write("app.log", 2 * 1024 * 1024)

        logger_module.cleanup_logs(retention_days=7, max_total_bytes=1024 * 1024)

        self.assertEqual(active.stat().st_size, 0)


class TestConsoleWithoutTty(unittest.TestCase):
    """TTY yokken prompt_toolkit çalışmamalı, komutlar stdin'den okunmalı."""

    def _make_console(self):
        with (
            patch.object(console_module, "FileHistory", MagicMock()),
            patch.object(console_module, "_trim_history_file"),
        ):
            return Console(MagicMock(), MagicMock())

    def test_non_tty_reads_commands_from_stdin(self):
        console = self._make_console()
        console._stdin_is_interactive = lambda: False  # type: ignore[method-assign]

        with (
            patch("sys.stdin", io.StringIO("show modules\nexit\n")),
            patch.object(console_module.logger, "info"),
        ):
            console.start()

        executed = [
            call.args[0] for call in console.command_manager.execute_command.call_args_list
        ]
        self.assertEqual([line.strip() for line in executed], ["show modules", "exit"])

    def test_prompt_errors_do_not_loop_forever(self):
        """Prompt sürekli hata verse de döngü sınırlı sayıda deneyip kapanmalı."""
        console = self._make_console()
        console.session = MagicMock()
        console.session.prompt.side_effect = RuntimeError("event loop kapandı")

        with (
            patch.object(console, "_stdin_is_interactive", return_value=True),
            patch.object(console_module, "PROMPT_RETRY_DELAY_SECONDS", 0),
            patch.object(console_module.logger, "info"),
            patch.object(console_module.logger, "exception") as mock_exception,
            patch.object(console_module.logger, "debug") as mock_debug,
        ):
            console.start()

        self.assertFalse(console.running)
        self.assertEqual(
            console.session.prompt.call_count,
            console_module.MAX_CONSECUTIVE_PROMPT_ERRORS,
        )
        # Ayrıntılı traceback yalnızca bir kez loglanmalı
        self.assertEqual(mock_exception.call_count, 1)
        self.assertEqual(
            mock_debug.call_count, console_module.MAX_CONSECUTIVE_PROMPT_ERRORS - 1
        )


if __name__ == "__main__":
    unittest.main()
