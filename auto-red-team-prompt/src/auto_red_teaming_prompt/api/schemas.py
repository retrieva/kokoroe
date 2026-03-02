"""API リクエストスキーマ定義モジュール。"""

from typing import Optional

from pydantic import BaseModel

from auto_red_teaming_prompt.data.utils import LengthLimit


class CommonRequest(BaseModel):
    """共通フィールドをまとめたベースリクエストモデル。"""

    model_type: str = "vllm"
    model_config_path: str
    output_path: Optional[str] = None
    sync: bool = False


class GenerateRedPromptRequest(CommonRequest):
    """攻撃プロンプトの作成リクエストモデル。"""

    risk_json_path: str
    use_web_search: bool = False
    length_pool: Optional[list[LengthLimit]] = None


class GenerateResponseRequest(CommonRequest):
    """攻撃の実行生成リクエストモデル。"""

    red_prompt_file: str


class EvaluateRequest(CommonRequest):
    """結果の評価リクエストモデル。"""

    evaluation_file: str


class SummaryRequest(CommonRequest):
    """結果の要約リクエストモデル。"""

    input_file: str
