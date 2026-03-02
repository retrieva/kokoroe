"""auto-red-team-promptのHTTP APIサーバ実装。"""

import json
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from auto_red_teaming_prompt.api import api_doc
from auto_red_teaming_prompt.api.schemas import (
    EvaluateRequest,
    GenerateRedPromptRequest,
    GenerateResponseRequest,
    SummaryRequest,
)
from auto_red_teaming_prompt.data import OutputPrompt, OutputResponse, SafetyClassificationResult, load_risk
from auto_red_teaming_prompt.models import get_llm, load_config_file
from scripts.run_evaluate_response import run_evaluation

# (2025/9/4) NOTE: リファクタリングもあるため、とりあえずスクリプトからインポート
from scripts.run_generate_red_prompt import run_generate_red_prompt
from scripts.run_generate_response import run_generate_response
from scripts.summary_safety_classification import (
    aggregate_qualitative_data,
    aggregate_quantitative_data,
    run_generate_summary,
)

# NOTE: フォルダ作られれば消す
TASK_DIR = Path("tmp/tasks")
TASK_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="auto-red-team-prompt API")


def _save_task(output_path: Path, payload: dict) -> None:
    """タスクの状態をファイルに保存します。"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _load_task(output_path: Path) -> dict:
    """タスクの状態をファイルから読み込みます。"""
    if not output_path.exists():
        raise FileNotFoundError
    with open(output_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _update_task_status(output_path: Path, **kwargs) -> None:
    """タスクの状態を更新します。"""
    try:
        data = _load_task(output_path)
    except FileNotFoundError:
        data = {"status": "pending", "response": None}
    data.update(kwargs)
    _save_task(output_path, data)


def _create_pending_task(output_path_arg: str | None, api_name: str | None) -> tuple[str, Path]:
    """新しいタスクを作成し、pending状態で保存する。"""
    task_id = str(uuid.uuid4())
    output_path = (TASK_DIR / output_path_arg) if output_path_arg else (TASK_DIR / f"{task_id}.json")
    _save_task(output_path, {"status": "pending", "api": api_name, "task_id": task_id, "response": None})
    return task_id, output_path


# NOTE: リファクタのPRと混ぜるときに_load系を共通化したい
def _load_red_prompt(red_prompt_file: str) -> dict[str, list[OutputPrompt]]:
    """指定されたファイルから攻撃プロンプトを読み込みます。"""
    # NOTE: /v1/generate_red_promptの出力結果をresponseに保存しているためutils/load_red_promptと差異が生じている
    with open(red_prompt_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    responses = data["response"]
    output = {}
    for category, prompts in responses.items():
        output[category] = [OutputPrompt(**item) for item in prompts]

    return output


def _load_evaluation_data(file_path: str) -> dict[str, list[dict[str, OutputPrompt | OutputResponse]]]:
    """指定されたファイルから評価データを読み込みます。"""
    # NOTE: /v1/generate_responseの出力結果をresponseに保存しているためrun_evaluate_response/load_evaluation_dataと差異が生じている
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    responses = data["response"]
    new_format_data: dict[str, list[dict[str, OutputPrompt | OutputResponse]]] = {}
    for category, items in responses.items():
        # TODO: フォーマット確認
        new_format_data[category] = [
            {
                "input": OutputPrompt(**item["input"]),
                "output": OutputResponse(**item["output"]),
            }
            for item in items
        ]
    return new_format_data


def _load_llm_data(
    input_file: str,
) -> dict[str, list[dict[str, OutputPrompt | OutputResponse | SafetyClassificationResult]]]:
    # NOTE: /v1/evaluateの出力結果をresponseに保存しているためsummary_safety_classification: load_llm_dataと差異が生じている
    """指定されたファイルから LLM の分類結果を読み込みます。"""
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    responses = data["response"]
    new_format_data: dict[str, list[dict[str, OutputPrompt | OutputResponse | SafetyClassificationResult]]] = {}
    for category, items in responses.items():
        new_format_data[category] = [
            {
                "input": OutputPrompt(**item["input"]),
                "output": OutputResponse(**item["output"]),
                "classification": SafetyClassificationResult(**item["classification"]),
            }
            for item in items
        ]
    return new_format_data


def _run_generate_red_prompt(output_path: Path, req: GenerateRedPromptRequest) -> None:
    """攻撃的なプロンプトを生成し、結果を保存する。"""
    _update_task_status(output_path, status="running")
    try:
        target_risks, length_pool = load_risk(req.risk_json_path)

        config = load_config_file(str(req.model_config_path), req.model_type)
        llm = get_llm(config)

        responses = run_generate_red_prompt(target_risks, llm, req.use_web_search, length_pool)
        out = jsonable_encoder(responses)

        _update_task_status(output_path, status="done", response=out)
    except Exception as e:
        _update_task_status(output_path, status="failed", error=str(e))


def _run_generate_response(output_path: Path, req: GenerateResponseRequest) -> None:
    """攻撃プロンプトに対する LLM 応答を生成し、結果を保存する。"""
    _update_task_status(output_path, status="running")
    try:
        prompts = _load_red_prompt(req.red_prompt_file)

        config = load_config_file(req.model_config_path, req.model_type)
        llm = get_llm(config)

        responses = run_generate_response(prompts, llm)
        out = jsonable_encoder(responses)

        _update_task_status(output_path, status="done", response=out)
    except Exception as e:
        _update_task_status(output_path, status="failed", error=str(e))


def _run_evaluation(output_path: Path, req: EvaluateRequest) -> None:
    """応答の安全性評価を実行し、結果を保存する。"""
    _update_task_status(output_path, status="running")
    try:
        evaluation_data = _load_evaluation_data(req.evaluation_file)

        config = load_config_file(req.model_config_path, req.model_type)
        llm = get_llm(config)

        responses = run_evaluation(evaluation_data, llm)
        out = jsonable_encoder(responses)

        _update_task_status(output_path, status="done", response=out)
    except Exception as e:
        _update_task_status(output_path, status="failed", error=str(e))


def _run_summary(output_path: Path, req: SummaryRequest) -> None:
    """評価結果を取りまとめて要約を生成し、結果を保存する。"""
    _update_task_status(output_path, status="running")
    try:
        llm_data = _load_llm_data(req.input_file)

        quantitative_summary = aggregate_quantitative_data(llm_data)
        qualitative_summary = aggregate_qualitative_data(llm_data)

        config = load_config_file(req.model_config_path, req.model_type)
        llm = get_llm(config)
        over_all_summary = run_generate_summary(quantitative_summary, llm)

        summary_data = {
            "overall-summary": over_all_summary,
            "quantitative-summary": jsonable_encoder(quantitative_summary),
            "qualitative-summary": jsonable_encoder(qualitative_summary),
        }

        _update_task_status(output_path, status="done", response=summary_data)
    except Exception as e:
        _update_task_status(output_path, status="failed", error=str(e))


@app.post("/v1/generate_red_prompt", description=api_doc.build_doc("generate_red_prompt"))
def generate(req: GenerateRedPromptRequest, background_tasks: BackgroundTasks):
    """攻撃的なプロンプトを生成するエンドポイント。"""
    task_id, output_path = _create_pending_task(req.output_path, api_name="/v1/generate_red_prompt")

    # 同期処理
    if req.sync:
        try:
            _run_generate_red_prompt(output_path, req)
            data = _load_task(output_path)
            if data.get("status") == "done":
                return JSONResponse(status_code=200, content={"responses": data.get("response")})
            raise HTTPException(status_code=500, detail=data.get("error", "failed"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    # 非同期処理
    background_tasks.add_task(_run_generate_red_prompt, output_path, req)
    status_url = f"/v1/tasks/{output_path.stem}"
    return JSONResponse(status_code=202, content={"task_id": task_id, "status_url": status_url})


@app.post("/v1/generate_response", description=api_doc.build_doc("generate_response"))
def generate_response(req: GenerateResponseRequest, background_tasks: BackgroundTasks):
    """攻撃プロンプトに対するLLM応答を生成するエンドポイント。"""
    task_id, output_path = _create_pending_task(req.output_path, api_name="/v1/generate_response")

    # 同期処理
    if req.sync:
        try:
            _run_generate_response(output_path, req)
            data = _load_task(output_path)
            if data.get("status") == "done":
                return JSONResponse(status_code=200, content={"responses": data.get("response")})
            raise HTTPException(status_code=500, detail=data.get("error", "failed"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    # 非同期処理
    background_tasks.add_task(_run_generate_response, output_path, req)
    status_url = f"/v1/tasks/{output_path.stem}"
    return JSONResponse(status_code=202, content={"task_id": task_id, "status_url": status_url})


@app.post("/v1/evaluate", description=api_doc.build_doc("evaluate"))
def evaluate(req: EvaluateRequest, background_tasks: BackgroundTasks):
    """応答の安全性評価を実行するエンドポイント。"""
    task_id, output_path = _create_pending_task(req.output_path, api_name="/v1/evaluate")

    # 同期処理
    if req.sync:
        try:
            _run_evaluation(output_path, req)
            data = _load_task(output_path)
            if data.get("status") == "done":
                return JSONResponse(status_code=200, content={"responses": data.get("response")})
            raise HTTPException(status_code=500, detail=data.get("error", "failed"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    # 非同期処理
    background_tasks.add_task(_run_evaluation, output_path, req)
    status_url = f"/v1/tasks/{output_path.stem}"
    return JSONResponse(status_code=202, content={"task_id": task_id, "status_url": status_url})


@app.post("/v1/summary", description=api_doc.build_doc("summary"))
def summary(req: SummaryRequest, background_tasks: BackgroundTasks):
    """評価結果を取りまとめて要約を生成するエンドポイント。"""
    task_id, output_path = _create_pending_task(req.output_path, api_name="/v1/summary")

    # 同期処理
    if req.sync:
        try:
            _run_summary(output_path, req)
            data = _load_task(output_path)
            if data.get("status") == "done":
                return JSONResponse(status_code=200, content={"responses": data.get("response")})
            raise HTTPException(status_code=500, detail=data.get("error", "failed"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    # 非同期処理
    background_tasks.add_task(_run_summary, output_path, req)
    status_url = f"/v1/tasks/{output_path.stem}"
    return JSONResponse(status_code=202, content={"task_id": task_id, "status_url": status_url})


@app.get("/v1/tasks/{file_name}", description=api_doc.build_doc("get_task"))
def get_task(file_name: str):
    """タスクのステータスを取得するエンドポイント。"""
    # TODO: ファイル名で取るようにしたがユニークでないため、task_idをデータベースで管理して使う方が良いかも
    file_name = Path(file_name).stem
    output_path = TASK_DIR / f"{file_name}.json"
    try:
        data = _load_task(output_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="task not found") from e
    return data
