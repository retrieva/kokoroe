# テストスイート

このディレクトリには、自動 Red Teaming システムの単体・統合テストが含まれます。現在のブランチでは全テストが安定してパスします（確認日: 2025-09-04）。

## ディレクトリ構造

```text
tests/
├── README.md                    # このファイル
├── fixtures/                    # テスト用データ
│   ├── sample.json              # サンプルリスクデータ
│   ├── sample-input.json        # サンプル入力データ
│   └── mock_responses.json      # モック応答データ
├── test_generators/             # Generator系のテスト
│   ├── test_simple.py           # 基本機能テスト
│   ├── test_real_data_basic.py  # 実データテスト
│   ├── test_red_prompt.py       # RedPromptGenerator
│   ├── test_response.py         # ResponseGenerator
│   ├── test_evaluator.py        # ResponseEvaluator
│   └── test_summarizer.py       # SafetySummarizer
├── test_integration.py          # パイプライン統合テスト
└── test_utils_common.py         # 共通ユーティリティ
```

## 実行方法（ローカル）

```bash
# すべてのテストを実行（推奨）
uv run pytest tests -v

# 変更確認用の軽量スモーク（一部のみ）
uv run pytest tests/test_generators/test_simple.py tests/test_generators/test_real_data_basic.py tests/test_utils_common.py -v

# コード品質チェック（任意）
uv run pre-commit run --all-files
```

## テストカテゴリ概要

- 基本/実データ: `test_simple.py`, `test_real_data_basic.py`
- ユーティリティ: `test_utils_common.py`（JSON I/O, LLM 初期化 など）
- 生成器系: `test_red_prompt.py`, `test_response.py`, `test_evaluator.py`, `test_summarizer.py`
- 統合: `test_integration.py`（FakeListLLM とパッチでパイプライン全体を検証）

## 現在のステータス

- 83 tests, 83 passed（2025-09-04 時点）
- 既知の不安定テスト: なし

注: テスト数は将来の追加/整理で変動します。最新の件数は上記コマンドの実行結果を参照してください。

## 🔗 関連

- `target-risks/`（実データのサンプル）
