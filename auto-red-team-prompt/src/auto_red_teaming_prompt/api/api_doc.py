"""API エンドポイント共通のドキュメント定義モジュール。"""

ENDPOINT_DOCS: dict[str, dict[str, object]] = {
    "generate_red_prompt": {
        "summary": "攻撃的なプロンプトを生成するエンドポイント。",
        "args": [
            "risk_json_path (str): リスク定義のJSONファイルへのパス",
            "use_web_search (bool): Web検索を使用するかどうかのフラグ",
            "length_pool (list[LengthLimit] | None): プロンプト長の制限",
        ],
    },
    "generate_response": {
        "summary": "攻撃プロンプトに対するLLM応答を生成するエンドポイント。",
        "args": ["red_prompt_file (str): 攻撃プロンプトファイルへのパス"],
    },
    "evaluate": {
        "summary": "応答の安全性評価を実行するエンドポイント。",
        "args": ["evaluation_file (str): 評価用データファイルへのパス"],
    },
    "summary": {
        "summary": "分類結果（evaluate の出力）を取りまとめて要約を生成するエンドポイント。",
        "args": ["input_file (str): 分類結果ファイルへのパス"],
    },
    "get_task": {
        "summary": "タスクのステータスを取得するエンドポイント。",
        "args": ["file_name (str): tmp/tasks 配下のtaskファイル名"],
    },
}


# 共通フラグメント
COMMON_ARGS = (
    "model_type (str): モデルの種類",
    "model_config_path (str): モデルの設定ファイルへのパス",
    "output_path (str | None): 出力ファイルのパス (None の場合は内部で生成)",
    "sync (bool): 同期処理を行うかどうかのフラグ",
)

COMMON_RETURNS_TASK = (
    "status: done (成功), running (実行中), failed (失敗)",
    "api: 呼び出されたAPIエンドポイントの名前",
    "task_id: タスクの一意なID",
    "response: 実行結果のデータ",
    "error: エラーメッセージ (statusがfailedの場合に含まれる)",
)

REQ_TYPE_MAP = {
    "generate_red_prompt": "GenerateRedPromptRequest",
    "generate_response": "GenerateResponseRequest",
    "evaluate": "EvaluateRequest",
    "summary": "SummaryRequest",
}


def build_doc(key: str) -> str:
    """指定キーのエンドポイント文言を返す。"""
    info = ENDPOINT_DOCS.get(key, {})
    summary = info.get("summary", "")
    args = info.get("args", [])
    returns = info.get("returns")
    req_type = REQ_TYPE_MAP.get(key, "")

    INDENT = "    "
    body_lines: list[str] = []
    body_lines.append("args:")
    if req_type:
        body_lines.append(f"{INDENT}req ({req_type}): リクエストボディ")
        for line in COMMON_ARGS:
            body_lines.append(f"{INDENT}- {line}")

    for arg in args:
        body_lines.append(f"{INDENT}- {arg}")

    body_lines.append("")
    body_lines.append("returns:")
    body_lines.append(f"{INDENT}JSONResponse: タスクIDやステータスなどを含むJSONレスポンス")

    if req_type:
        for line in COMMON_RETURNS_TASK:
            body_lines.append(f"{INDENT}- {line}")

    # TODO: 今は未使用、今後APIが増えた時用
    if returns:
        for line in returns.splitlines():
            if line not in body_lines:
                body_lines.append(line)

    body = "\n".join(body_lines)

    if summary:
        return f"{summary}\n\n```text\n{body}\n```"
    return f"```text\n{body}\n```"
