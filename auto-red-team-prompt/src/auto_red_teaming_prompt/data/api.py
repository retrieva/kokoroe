"""API 利用のみで使用するデータ一覧"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class ProgressStats:
    """進捗状況の統計情報を保持するデータクラス。"""

    elapsed_seconds: int
    total_seconds: int
    progress_percentage: float
    remaining_seconds: int
    status: Literal["ready", "running", "completed"]
