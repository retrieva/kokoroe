# Auto Red Teaming Prompt

与えられた攻撃シナリオに基づいて、Red Team の攻撃プロンプトを自動生成します。

また、Red Team プロンプトを用いて攻撃を実行し、その結果を評価・サマリ化する機能も提供します。

その結果から、Blue Team に向けた LLM 学習データを生成する機能（Blue Team）も実装しています。

## 使い方

開発環境は uv を利用していますが、単純に動かすだけなら `pip install .` でインストールできます。

uv を使う場合は、以下のコマンドで起動します。

```bash
$ uv sync
```

### [Option] LLMサーバーの起動
vLLMを利用したLLMサーバーを起動する場合は、以下のコマンドを実行します。

```bash
$ uv run vllm serve ${MODEL_NAME}
```

`http://localhost:8000` でサーバーが起動します。

KOKOROEのLLMサーバー設定では、以下のように設定してください。

```json
{
  "model_name": "${MODEL_NAME}",
  "openai_api_base": "http://localhost:8000/v1"
}
```

## Red Team について

与えられた攻撃シナリオに基づいて、Red Team の攻撃プロンプトを自動生成します。

また、Red Team プロンプトを用いて攻撃を実行し、その結果を評価・サマリ化する機能も提供します。

なお、本 Red Team 機能は **検証したい LLM（Target）** と **評価を行う LLM（Evaluator）** が用意されていることを前提としています。

### 動かし方の例

1. 攻撃プロンプトの作成
2. 攻撃の実行
3. 結果の評価
4. サマリの作成

また、以下のスクリプトを実行する際、 `--progress_report` フラグを追加すると、進捗状況が標準出力に表示されます。

#### 1. 攻撃プロンプトの作成

`scripts/run_generate_red_prompt.py` を実行することで、攻撃プロンプトを生成できます。

```bash
# uv 使わない場合は python ... としてください
uv run python scripts/run_generate_red_prompt.py \
    --model_type vllm \
    --model_config_file configs/vllm-online/${Evaluator-LLM}.json \  # 攻撃プロンプトを作成したい LLM
    --risk_json target-risks/sample.json \  # 入力攻撃シナリオ
    --output_path hoge.json \  # 出力先
    --log-level INFO  # ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
```

作成した攻撃プロンプト例は `target-risks/sample-red-prompt.json` を参照してください。

#### 2. 攻撃の実行

`scripts/run_generate_response.py` を実行することで、生成した攻撃プロンプトを用いて攻撃を実行できます。

```bash
# uv 使わない場合は python ... としてください
uv run python scripts/run_generate_response.py \
  --red_prompt_file hoge.json \  # 生成した攻撃プロンプト
  --model_type vllm \
  --model_config_file configs/vllm-online/${Target-LLM}.json \  # 攻撃対象となる LLM
  --output_file fuga.json \ # 出力先
  --log-format json --verbose  # JSONログで詳細出力
```

#### 3. 結果の評価

`scripts/run_evaluate_response.py` を実行することで、攻撃結果を評価できます。

```bash
# uv 使わない場合は python ... としてください
uv run python scripts/run_evaluate_response.py \
  --evaluation_file fuga.json \  # 攻撃結果
  --model_type vllm \
  --model_config_file configs/vllm-online/${Evaluator-LLM}.json \  # 評価に用いる LLM
  --output_file piyo.json \ # 出力先
  --quiet  # エラーログのみ出力
```

#### 4. サマリの作成

`scripts/summary_safety_classification.py` を実行することで、評価結果のサマリを作成できます。

```bash
# uv 使わない場合は python ... としてください
uv run python scripts/summary_safety_classification.py \
  --input_file piyo.json \  # 評価結果
  --output_file summary.json \ # 出力先
  --model_type vllm \
  --model_config_file configs/vllm-online/${Evaluator-LLM}.json \ # サマリ作成に用いる LLM
  --log-file summary.log  # ログをファイルへ出力
```

## Blue Team について

Red Team の結果から、Blue Team に向けた LLM 学習データを生成する機能（Blue Team）を実装しています。

Blue Team 機能についても **改善したい LLM（Target）** と **評価を行う LLM（Evaluator）** が用意されていることを前提としています。

### 動かし方の例

1. Red Team 結果から LLM の理想的な振る舞い（Constitution）を生成
2. Red Team 結果を反映した攻撃プロンプトを生成
3. 対応する LLM の応答を生成
4. 作成した応答について、Constitution に基づいて修正を実施
5. 作成したデータを学習データとして保存

また、以下のスクリプトを実行する際、 `--progress_report` フラグを追加すると、進捗状況が標準出力に表示されます。

#### 1. Constitution の生成

`scripts/blue-teaming/run_pre_process.py` を実行することで、Red Team 結果から LLM の理想的な振る舞い（Constitution）を生成できます。

```bash
# uv 使わない場合は python ... としてください
uv run python scripts/blue-teaming/run_pre_process.py \
  --model_type vllm \
  --model_config_file configs/vllm-online/${Evaluator-LLM}.json \  # Constitution 作成に用いる LLM
  --input_data input_data.json \  # Red Team の入出力（詳細は以下に記載）
  --constitution_output_path constitution.json \  # Constitution 出力先
  --summary_output_path summary.json \  # サマリ出力先
```


入力に使用する `input_data.json` は以下のようなものを想定しています。具体的な例は `target-risks/blue-teaming/sample-input.json` に記載しています。

```json
{
  "attack-scenario": list[dict],  # Red Team に与えた攻撃シナリオのリスト
  "quantitative-summary": dict[str, dict], # Red Team の攻撃結果の定量的サマリ
  "llm-constitutions": list[str]  # Red Team に関係なく、LLM の理想的な振る舞いを示す Constitution のリスト（このリストに対して変更が加えられる）
}
```

また、このスクリプトは `constitution_output_path` に Constitution を、 `summary_output_path` に Red Team 結果のサマリを出力します。

作成した Constitution の例は `target-risks/blue-teaming/sample-constitution.json` に記載しています。

作成したサマリの例は `target-risks/blue-teaming/sample-summary.json` に記載しています。

#### 2. 攻撃プロンプトの生成

`scripts/blue-teaming/run_generate_red_prompt.py` を実行することで、Red Team 結果を反映した攻撃プロンプトを生成できます。

```bash
# uv 使わない場合は python ... としてください
uv run python scripts/blue-teaming/run_generate_red_prompt.py \
  --model_type vllm \
  --model_config_file configs/vllm-online/${Evaluator-LLM}.json \  # 攻撃プロンプト作成に用いる LLM
  --risk_json target-risks/sample.json \  # 入力攻撃シナリオ（Red Team に与えたものと同じ）
  --vulnerability_summary summary.json \  # Red Team 結果のサマリ（前ステップで作成したもの）
  --output_path red_prompt_for_blue.json
```

#### 3. 応答の生成

応答の生成は、Red Team と同様に `scripts/run_generate_response.py` を実行します。

```bash
# uv 使わない場合は python ... としてください
uv run python scripts/run_generate_response.py \
  --red_prompt_file red_prompt_for_blue.json \  # 生成した攻撃プロンプト
  --model_type vllm \
  --model_config_file configs/vllm-online/${Target-LLM}.json \  # 攻撃対象となる LLM
  --output_file response.json \  # 出力先
  --log-format json --verbose  # JSONログで詳細出力
```

#### 4. 応答の修正

3で作成した応答は当然ながら不適切な出力を含んでいる可能性があります。そこで、
`scripts/blue-teaming/run_generate_training_data.py` を実行することで、Constitution に基づいて応答の修正を実施します。

```bash
# uv 使わない場合は python ... としてください
uv run python scripts/blue-teaming/run_generate_training_data.py \
  --model_type vllm \
  --model_config_file configs/vllm-online/${Evaluator-LLM}.json \  # 修正に用いる LLM
  --constitution_file constitution.json \  # Constitution ファイル（ステップ1で作成したもの） \
  --generator_output_file response.json \  # 3で作成した応答ファイル
  --output_file corrected_responses.json  # 修正後の応答出力先
```

#### 5. 学習データの保存

4で作成したデータを学習データ（SFT/DPO）として保存します。
作成した学習データは OpenAI のファインチューニング用データフォーマットに準拠しています。
スクリプトは `scripts/blue-teaming/run_post_process.py` です。

```bash
# uv 使わない場合は python ... としてください
uv run python scripts/blue-teaming/run_post_process.py \
  --training_data_path corrected_responses.json \  # 4で作成した修正後の応答ファイル
  --output_sft_data_path blue_team_sft_data.json \  # 学習データ出力先（SFT 用フォーマット）
  --output_dpo_data_path blue_team_dpo_data.json \  # 学習データ出力先（DPO 用フォーマット）
  --constitution_path constitution.json \  # Constitution ファイル（ステップ1で作成したもの）
  --vulnerability_summary_path summary.json \  # Red Team 結果のサマリ（ステップ1で作成したもの）
  --output_report_path blue_team_data_report.json  # 学習データのレポート出力先
```

出力ファイル `output_report_path` には、作成した学習データの統計情報などが含まれます。
詳細は `target-risks/blue-teaming/sample-output.json` を参照してください。

## ログ出力について

CLI スクリプトは以下のフラグでログを制御できます。

- `--log-level`: ログレベル（DEBUG/INFO/…）。`--verbose` は DEBUG、`--quiet` は ERROR に相当。
- `--log-format`: `text`（既定）または `json`。
- `--log-file`: 指定時はファイル出力、未指定時は stderr 出力。

ライブラリ側は `logging.getLogger(__name__)` を用い、グローバル設定は行いません。

## Generator の共通インタフェース

`auto_red_teaming_prompt.generators.BaseGenerator` を継承し、以下のメソッドを実装します。

- `generate(self, input_data: T) -> R`: 生成処理本体。
- `save_results(self, results: R, output_path: str) -> None`: 永続化処理。

既存実装については、 `src/auto_red_teaming_prompt/generators` 以下を参照してください。
