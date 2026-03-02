"""API の進行を出力する"""

import json
import sys
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import asdict
from typing import Generator

from tqdm import tqdm

from auto_red_teaming_prompt.data import ProgressStats

STOP_EVENT_CHECK_INTERVAL = 1.0  # seconds


class _State:
    """進捗報告の状態を管理する内部クラス"""

    def __init__(self):
        """初期化"""
        self.start_time = time.time()
        self.estimated_total = None
        self.progress = 0.0
        self.running = False


class BaseReporter(ABC):
    """進捗報告の基底クラス"""

    @abstractmethod
    def ticking(self):
        """進捗報告の開始と終了を管理するコンテキストマネージャー"""
        pass

    @abstractmethod
    def update_finish_time(self, estimated_total_seconds: int | None) -> None:
        """完了予想時間を更新する"""
        pass

    @abstractmethod
    def update_progress(self, progress: float) -> None:
        """進捗状況を更新する"""
        pass


class NullReporter(BaseReporter):
    """無効に使うためのダミークラス。"""

    @contextmanager
    def ticking(self):
        """進捗報告の開始と終了を管理するコンテキストマネージャー"""
        yield

    def update_finish_time(self, estimated_total_seconds: int | None) -> None:
        """完了予想時間を更新する"""
        pass

    def update_progress(self, progress: float) -> None:
        """進捗状況を更新する"""
        pass


class ProgressReporter(BaseReporter):
    """Json 形式で進捗を標準出力に報告するクラス。"""

    def __init__(self):
        """初期化"""
        self._state = _State()
        self._stop_event = threading.Event()
        self._thread = None

    def _loop(self) -> None:
        """進捗報告を行う"""
        while not self._stop_event.is_set():
            elapsed = int(time.time() - self._state.start_time)
            total = self._state.estimated_total or 0
            remaining = max(total - elapsed, 0) if total else None
            report = ProgressStats(
                elapsed_seconds=elapsed,
                total_seconds=total,
                progress_percentage=round((self._state.progress or 0.0) * 100.0, 2),
                remaining_seconds=remaining if remaining is not None else -1,
                status="running" if not self._stop_event.is_set() else "completed",
            )
            sys.stdout.write(json.dumps(asdict(report), ensure_ascii=False) + "\n")
            sys.stdout.flush()
            self._stop_event.wait(STOP_EVENT_CHECK_INTERVAL)

        elapsed = int(time.time() - self._state.start_time)
        final_report = ProgressStats(
            elapsed_seconds=elapsed,
            total_seconds=elapsed,
            progress_percentage=100.0,
            remaining_seconds=0,
            status="completed",
        )
        sys.stdout.write(json.dumps(asdict(final_report), ensure_ascii=False) + "\n")
        sys.stdout.flush()

    @contextmanager
    def ticking(self) -> Generator[None, None, None]:
        """進捗報告の開始と終了を管理するコンテキストマネージャー"""
        self._state.start_time = time.time()
        self._state.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        try:
            yield
        finally:
            # Ensure the reporting thread is stopped
            self._stop_event.set()
            self._thread.join(timeout=2.0)
            self._state.running = False

    def update_finish_time(self, estimated_total_seconds: int | None) -> None:
        """完了予想時間を更新する"""
        self._state.estimated_total = int(estimated_total_seconds) if estimated_total_seconds is not None else None

    def update_progress(self, progress: float) -> None:
        """進捗状況を更新する"""
        progress = max(0.0, min(1.0, float(progress)))
        if progress < (self._state.progress or 0.0):
            return  # 進捗が後退することはないようにする

        self._state.progress = progress


class ProgressEstimator(ABC):
    """進捗を推定するための基底クラス"""

    @abstractmethod
    @contextmanager
    def batch(self, batch_size: int):
        """1バッチ分の処理を包むコンテキスト"""
        pass


class NullProgressEstimator(ProgressEstimator):
    """無効に使うためのダミークラス。"""

    @contextmanager
    def batch(self, batch_size: int):
        """1バッチ分の処理を包むコンテキスト"""
        yield


class TimeBasedProgressEstimator(ProgressEstimator):
    """時間ベースで progress を滑らかに更新する補助クラス"""

    past_weight = 0.7  # 移動平均の過去側の重み
    current_weight = 0.3  # 移動平均の現在側の重み

    def __init__(self, total_items: int, reporter: BaseReporter):
        """初期化"""
        self.total_items = total_items
        self.reporter = reporter

        self._lock = threading.Lock()
        self._completed_real = 0  # 実際に終わった件数（pbar.update 済み）
        self._sec_per_item: float | None = None  # 推定 1件あたり時間

    @contextmanager
    def batch(self, batch_size: int):
        """1バッチ分の処理を包むコンテキスト

        - バッチ中は推定 progress を 1秒ごとに更新
        - バッチ終了時に実測時間から sec_per_item を更新
        """
        start_time = time.time()
        stop_event = threading.Event()

        # スレッドで「見かけの進捗」を更新
        thread = threading.Thread(
            target=self._loop_batch,
            args=(batch_size, start_time, stop_event),
            daemon=True,
        )
        thread.start()
        try:
            yield  # ここで実際の heavy な処理（chain.batch 等）をやる
        finally:
            stop_event.set()
            thread.join(timeout=2.0)

            # バッチ全体の実測時間から sec_per_item を更新
            elapsed = time.time() - start_time
            per_item = elapsed / max(batch_size, 1)

            with self._lock:
                if self._sec_per_item is None:
                    self._sec_per_item = per_item
                else:
                    # 移動平均でならす
                    self._sec_per_item = self.past_weight * self._sec_per_item + self.current_weight * per_item

                # 実際に終わった件数として加算
                self._completed_real += batch_size

                # 最終的な「本当の」進捗を報告（見かけの値にスナップ）
                self._update_progress(self._completed_real)

    def _loop_batch(self, batch_size: int, start_time: float, stop_event: threading.Event):
        """バッチ処理中に、推定 progress を1秒ごとに更新するループ"""
        while not stop_event.is_set():
            with self._lock:
                if self._sec_per_item is None:
                    # まだ最初のバッチが終わっていないなどで推定不能
                    pass
                else:
                    elapsed = time.time() - start_time
                    est_done_in_batch = int(elapsed / self._sec_per_item)

                    # バッチサイズが 100 のときは 0〜99 の範囲でしか進めない
                    est_done_in_batch = max(0, min(est_done_in_batch, batch_size - 1))

                    # 見かけ上の全体完了件数（実際に終わった分 + バッチ内での推定分）
                    display_done = self._completed_real + est_done_in_batch
                    display_done = min(display_done, self.total_items - 1)  # 100% にはしない

                    self._update_progress(display_done)

            stop_event.wait(STOP_EVENT_CHECK_INTERVAL)

    def _update_progress(self, done_items: int):
        progress = done_items / self.total_items if self.total_items > 0 else 0.0
        self.reporter.update_progress(progress)


def tqdm_bridge(pbar: tqdm, reporter: BaseReporter) -> tuple[threading.Thread, threading.Event]:
    """Tqdm の進捗を ProgressReporter に同期させるためのコンテキストマネージャー

    Args:
        pbar: tqdm プログレスバーのインスタンス
        reporter: 進捗報告用の BaseReporter インスタンス
    Returns:
        進捗同期用のスレッドと停止用のイベント
    Example:
        ```python
        with tqdm(total=100) as pbar:
            thread, stop_event = tqdm_bridge(pbar, reporter)
            try:
                for i in range(100):
                    # 何らかの処理
                    pbar.update(1)
            finally:
                stop_event.set()
                thread.join(timeout=1.0)
        ```

    """
    stop_event = threading.Event()

    def loop():
        while not stop_event.is_set():
            fmt = getattr(pbar, "format_dict", {}) or {}
            elapsed = fmt.get("elapsed", 0.0) or 0.0
            remaining = fmt.get("remaining", None)

            if remaining is not None:
                reporter.update_finish_time(int(elapsed + remaining))

            total = pbar.total or 0
            n = pbar.n or 0
            if total > 0:
                reporter.update_progress(n / total)

            stop_event.wait(STOP_EVENT_CHECK_INTERVAL)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread, stop_event


@contextmanager
def report_with_tqdm(
    total: int, desc: str, unit: str, logger_enabled: bool, reporter: BaseReporter
) -> Generator[tqdm, None, None]:
    """Tqdm の処理とブリッジをまとめて管理するコンテキストマネージャー

    Args:
        total: tqdm の total 値
        desc: tqdm の説明文
        unit: tqdm の単位
        logger_enabled: ロガーが有効かどうか
        reporter: 進捗報告用の BaseReporter インスタンス
    Yields:
        tqdm プログレスバーのインスタンス
    Example:
        ```python
            with report_with_tqdm(
                total=100,
                desc="Processing",
                unit="item",
                logger_enabled=True,
                reporter=reporter
            ) as pbar:
                for i in range(100):
                    # 何らかの処理
                    pbar.update(1)
        ```

    """
    with tqdm(total=total, desc=desc, unit=unit, disable=not logger_enabled) as pbar:
        thread_bridge, stop_bridge = tqdm_bridge(pbar, reporter)
        try:
            yield pbar
        finally:
            stop_bridge.set()
            thread_bridge.join(timeout=2.0)
