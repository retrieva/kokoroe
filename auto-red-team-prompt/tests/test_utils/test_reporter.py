"""utils.reporter に関する単体テスト"""

import json
import time

import pytest

import auto_red_teaming_prompt.utils.reporter as mod_reporter


@pytest.fixture(autouse=True)
def redefine_interval(monkeypatch):
    """STOP_EVENT_CHECK_INTERVAL を短くしてテストを高速化する"""
    monkeypatch.setattr(mod_reporter, "STOP_EVENT_CHECK_INTERVAL", 0.01)
    yield


class SpyReporter(mod_reporter.BaseReporter):
    """お手軽に動作確認できるようにするためのスパイクラス"""

    def __init__(self):
        """初期化"""
        self.finish_times = []
        self.progresses = []
        self._ctx_depth = 0

    def ticking(self):
        """コンテキストマネージャーのスパイ実装"""

        class _Ctx:
            def __enter__(_self):
                self._ctx_depth += 1

            def __exit__(_self, *ext):
                self._ctx_depth -= 1

        return _Ctx()

    def update_finish_time(self, estimated_total_seconds: int | None):
        """完了予想時間を記録する"""
        self.finish_times.append(estimated_total_seconds)

    def update_progress(self, progress: float):
        """進捗状況を記録する"""
        self.progresses.append(progress)


def parse_json_lines(output: str):
    """JSON Lines 形式の文字列をパースして辞書のリストを返すヘルパー関数"""
    return [json.loads(line) for line in output.strip().splitlines() if line.strip()]


class TestNullReporter:
    """NullReporter のテストクラス"""

    def test_output(self, capsys):
        """NullReporter は出力を行わないことを確認する"""
        reporter = mod_reporter.NullReporter()
        with reporter.ticking():
            reporter.update_progress(0.1)
            reporter.update_finish_time(10)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestProgressReporter:
    """ProgressReporter のテストクラス"""

    def test_output(self, capsys):
        """ProgressReporter は進捗を出力することを確認する"""
        reporter = mod_reporter.ProgressReporter()
        with reporter.ticking():
            reporter.update_progress(0.5)
            time.sleep(0.1)
            reporter.update_progress(1.0)
            time.sleep(0.1)
        captured = capsys.readouterr().out
        rows = parse_json_lines(captured)
        assert len(rows) >= 2
        # 最初の行は 50% の進捗
        assert any(row["progress_percentage"] >= 50.0 for row in rows)
        assert rows[0]["status"] == "running"
        # 最後の行は 100% の進捗で完了状態
        assert rows[-1]["progress_percentage"] == 100.0
        assert rows[-1]["status"] == "completed"
        assert rows[-1]["remaining_seconds"] == 0

    def test_progress_clamp(self, capsys):
        """進捗が 0-1 の範囲にクランプされることを確認する"""
        reporter = mod_reporter.ProgressReporter()
        with reporter.ticking():
            reporter.update_progress(-0.5)  # 下限を下回る
            time.sleep(0.1)
            reporter.update_progress(1.5)  # 上限を上回る
            time.sleep(0.1)
        captured = capsys.readouterr().out
        rows = parse_json_lines(captured)
        for row in rows:
            assert 0.0 <= row["progress_percentage"] <= 100.0


class TestTqdmBridge:
    """tqdm_bridge 関数のテストクラス"""

    def test_bridge_updates_reporter(self):
        """Tqdm の進捗が ProgressReporter に反映されることを確認する"""

        class FakePbar:
            def __init__(self):
                self.total = 10
                self.n = 0
                self.format_dict = {"elapsed": 0, "remaining": None}

        pbar = FakePbar()
        spy = SpyReporter()
        thread, stop_event = mod_reporter.tqdm_bridge(pbar, spy)
        try:
            time.sleep(0.1)
            assert spy.finish_times == []

            # pbar を進める
            pbar.n = 3
            pbar.format_dict["elapsed"] = 1.0
            pbar.format_dict["remaining"] = 2.0
            time.sleep(0.1)

            # finish_time と progress が更新されていることを確認
            assert any(finish_time >= 3 for finish_time in spy.finish_times)
            assert any(progress >= 0.2 for progress in spy.progresses)
        finally:
            stop_event.set()
            thread.join(timeout=1.0)


class TestReportWithTqdm:
    """report_with_tqdm コンテキストマネージャーのテストクラス"""

    def test_context_manager(self, capsys):
        """report_with_tqdm コンテキストマネージャーの動作確認"""
        reporter = mod_reporter.ProgressReporter()
        total = 5
        with reporter.ticking():
            with mod_reporter.report_with_tqdm(
                total=total,
                desc="Testing",
                unit="item",
                logger_enabled=True,
                reporter=reporter,
            ) as pbar:
                for _ in range(total):
                    time.sleep(0.1)
                    pbar.update(1)

        output = capsys.readouterr().out
        rows = parse_json_lines(output)

        assert rows[-1]["status"] == "completed"
        assert rows[-1]["progress_percentage"] == 100.0

    def test_context_manager_disabled_logger(self, capsys):
        """logger_enabled=False の場合でも問題なく動作することを確認"""
        reporter = mod_reporter.ProgressReporter()
        total = 5
        with reporter.ticking():
            with mod_reporter.report_with_tqdm(
                total=total,
                desc="Testing",
                unit="item",
                logger_enabled=False,
                reporter=reporter,
            ) as pbar:
                for _ in range(total):
                    time.sleep(0.1)
                    pbar.update(1)

        output = capsys.readouterr().out
        rows = parse_json_lines(output)

        assert rows[-1]["progress_percentage"] == 100.0
