require "json"
require "tempfile"

class Attack::ExecutionClient
  # テスト用: 次のリクエストを失敗させるフラグ
  cattr_accessor :force_next_failure
  self.force_next_failure = false

  def self.call_attack(scenario_hash, execution_id: nil)
    if use_dummy?
      call_dummy_attack(scenario_hash, execution_id: execution_id)
    else
      call_real_attack(scenario_hash, execution_id: execution_id)
    end
  end

  private

  def self.use_dummy?
    ENV["USE_DUMMY_ATTACK"] == "true"
  end

  def self.call_dummy_attack(scenario_hash, execution_id: nil)
    # テスト用: 強制失敗フラグのチェック
    if force_next_failure
      self.force_next_failure = false # フラグをリセット
      raise StandardError, "Forced failure for testing"
    end

    # ダミー実行のログ出力
    Rails.logger.info "[DUMMY ATTACK] Starting dummy attack execution"
    Rails.logger.info "[DUMMY ATTACK] Scenario: #{scenario_hash}"

    # 開始日時を更新
    if execution_id
      execution = Attack::Execution.find(execution_id)
      ProgressHelper.broadcast_started_at(
        progress_id: execution_id,
        started_at: execution.started_at
      )
    end

    # 処理時間のシミュレート（1秒ごとに10%進捗）
    10.times do |i|
      percentage = (i + 1) * 10
      status = case percentage
      when 0..30 then "攻撃プロンプトを準備中..."
      when 31..60 then "攻撃を実行中..."
      when 61..100 then "結果を評価中..."
      end

      # 進捗を送信
      if execution_id
        ProgressHelper.broadcast_progress(
          progress_id: execution_id,
          percentage: percentage,
          status: status
        )
      end

      sleep(Attack::DummyClientConfig.progress_sleep_duration)
    end

    # ダミーのレスポンスハッシュを返す
    # 実際のPythonスクリプト出力に合わせた形式:
    # - トップレベルキー: ハイフン形式
    # - ネストされたキー: アンダースコア形式（dataclassのフィールド名）
    {
      response: {
        "overall-summary" => "quantitative summary と qualitative summary をベースにした要約文書",
        "quantitative-summary" => {
          "Hate/Hate-Speech/Race" => {
            "number_of_successes" => 2,
            "number_of_attacks" => 4,
            "success_rate" => 0.5
          },
          "Deception/Fraud/Spam" => {
            "number_of_successes" => 1,
            "number_of_attacks" => 3,
            "success_rate" => 0.33
          }
        },
        "qualitative-summary" => {
          "Hate/Hate-Speech/Race" => {
            "attack_success_examples" => [
              { "prompt" => "攻撃が成功した例1", "response" => "攻撃の成功に関する応答1" },
              { "prompt" => "攻撃が成功した例2", "response" => "攻撃の成功に関する応答2" }
            ],
            "guard_success_examples" => [
              { "prompt" => "攻撃が防御された例1", "response" => "防御の成功に関する応答1" },
              { "prompt" => "攻撃が防御された例2", "response" => "防御の成功に関する応答2" }
            ]
          },
          "Deception/Fraud/Spam" => {
            "attack_success_examples" => [
              { "prompt" => "詐欺が成功した例1", "response" => "詐欺の成功に関する応答1" }
            ],
            "guard_success_examples" => [
              { "prompt" => "詐欺が防御された例1", "response" => "防御の成功に関する応答1" },
              { "prompt" => "詐欺が防御された例2", "response" => "防御の成功に関する応答2" }
            ]
          }
        },
        "other-stats" => {
          "time" => {
            "run-attack" => 600,
            "evaluation-output" => 300
          },
          "token-length" => {
            "20" => 50,
            "40" => 20
          },
          "generated-samples" => [
            {
              "prompt" => "攻撃プロンプト",
              "category" => "Hate/Hate-Speech/Race",
              "response" => "攻撃に対する応答",
              "evaluation" => {
                "success" => true,
                "reason" => "true と判断した理由"
              }
            },
            {
              "prompt" => "攻撃プロンプト",
              "category" => "Hate/Hate-Speech/Race",
              "response" => "攻撃に対する応答",
              "evaluation" => {
                "success" => true,
                "reason" => "true と判断した理由"
              }
            },
            {
              "prompt" => "攻撃プロンプト",
              "category" => "Hate/Hate-Speech/Race",
              "response" => "攻撃に対する応答",
              "evaluation" => {
                "success" => false,
                "reason" => "false と判断した理由"
              }
            },
            {
              "prompt" => "攻撃プロンプト",
              "category" => "Hate/Hate-Speech/Race",
              "response" => "攻撃に対する応答",
              "evaluation" => {
                "success" => false,
                "reason" => "false と判断した理由"
              }
            },
            {
              "prompt" => "攻撃プロンプト",
              "category" => "Deception/Fraud/Spam",
              "response" => "攻撃に対する応答",
              "evaluation" => {
                "success" => false,
                "reason" => "false と判断した理由"
              }
            },
            {
              "prompt" => "攻撃プロンプト",
              "category" => "Deception/Fraud/Spam",
              "response" => "攻撃に対する応答",
              "evaluation" => {
                "success" => true,
                "reason" => "true と判断した理由"
              }
            },
            {
              "prompt" => "攻撃プロンプト",
              "category" => "Deception/Fraud/Spam",
              "response" => "攻撃に対する応答",
              "evaluation" => {
                "success" => false,
                "reason" => "false と判断した理由"
              }
            }
          ]
        }
      }
    }
  end

  def self.config
    AiModelConfig::EVALUATION_LLM
  end

  def self.target_config
    Rails.env.production? ? AiModelConfig::TARGET_LLM_PRODUCTION : AiModelConfig::TARGET_LLM_DEVELOPMENT
  end

  def self.call_real_attack(scenario_hash, execution_id: nil)
    # 本番の外部システム呼び出し
    Rails.logger.info "[REAL ATTACK] Calling external attack system"
    Rails.logger.info "[REAL ATTACK] Scenario: #{scenario_hash}"

    # python3コマンドの存在確認
    python_available = system("which python3 > /dev/null 2>&1")
    unless python_available
      Rails.logger.error "Error: python3 command not found"
      return {
        status: "error",
        message: "python3 command not found",
        timestamp: Time.current.iso8601
      }
    end

    begin
      # scenario_hashを攻撃プロンプトファイルとして保存
      # scenario_hashはプロンプトの配列: [{category: "...", text: "..."}, ...]
      red_prompt_file = Tempfile.new([ "red_prompt", ".json" ])
      output_file = Tempfile.new([ "attack_response", ".json" ])
      evaluation_output_file = Tempfile.new([ "evaluation_result", ".json" ])
      summary_output_file = Tempfile.new([ "summary_result", ".json" ])

      # プロンプトをPythonスクリプトが期待するフォーマットに変換
      # カテゴリごとにグループ化: { "category1" => [{prompt: "...", ...}], ... }
      prompts_by_category = scenario_hash.group_by { |p| p[:category] }
      formatted_prompts = prompts_by_category.transform_values do |prompts|
        prompts.map do |p|
          {
            prompt: p[:text],
            category: p[:category]
          }
        end
      end

      # デバッグ: JSONファイルの内容を出力
      json_content = JSON.pretty_generate(formatted_prompts)
      Rails.logger.debug "[REAL ATTACK] Red prompt JSON content:"
      Rails.logger.debug json_content

      red_prompt_file.write(json_content)
      red_prompt_file.flush

      # 開始日時を更新
      if execution_id
        execution = Attack::Execution.find(execution_id)
        ProgressHelper.broadcast_started_at(
          progress_id: execution_id,
          started_at: execution.started_at
        )
      end

      begin
        # 攻撃の実行 (run_generate_response.py)
        Rails.logger.info "[REAL ATTACK] Executing attack with red prompts"

        if execution_id
          Attack::Execution.find(execution_id).update!(current_step: 1)
        end

        cmd = [
          "python3",
          "-u",
          "auto-red-team-prompt/scripts/run_generate_response.py",
          "--progress_report",
          "--red_prompt_file", red_prompt_file.path,
          "--model_type", "vllm",
          "--model_config_file", target_config.file_path,
          "--output_file", output_file.path,
          "--log-format", "json"
        ]

        IO.popen(cmd, err: [ :child, :out ]) do |io|
          io.each_line do |line|
            begin
              data = JSON.parse(line)
              # JSON形式の進捗データの場合
              if data["progress_percentage"]
                # ステップ2の進捗を0〜50%にスケーリング
                scaled_percentage = (data["progress_percentage"].to_f / 100 * 50).round
                Rails.logger.info "Progress: #{scaled_percentage}% - 攻撃を実行中..."

                # 進捗を送信
                if execution_id
                  ProgressHelper.broadcast_progress(
                    progress_id: execution_id,
                    percentage: scaled_percentage,
                    status: "攻撃を実行中..."
                  )
                end
              else
                Rails.logger.info "Python JSON: #{line.chomp}"
              end
            rescue JSON::ParserError
              # JSON以外の出力（通常のメッセージなど）
              Rails.logger.info "Python output: #{line.chomp}"
            end
          end
        end

        # 結果の評価 (run_evaluate_response.py)
        Rails.logger.info "[REAL ATTACK] Evaluating attack results"

        if execution_id
          Attack::Execution.find(execution_id).update!(current_step: 2)
          ProgressHelper.broadcast_progress(
            progress_id: execution_id,
            percentage: 50,
            status: "結果を評価中..."
          )
        end

        eval_cmd = [
          "python3",
          "-u",
          "auto-red-team-prompt/scripts/run_evaluate_response.py",
          "--evaluation_file", output_file.path,
          "--model_type", "vllm",
          "--model_config_file", config.file_path,
          "--output_file", evaluation_output_file.path,
          "--log-format", "json"
        ]

        IO.popen(eval_cmd, err: [ :child, :out ]) do |io|
          io.each_line do |line|
            Rails.logger.info "Python output (eval): #{line.chomp}"
          end
        end

        # サマリの作成 (summary_safety_classification.py)
        Rails.logger.info "[REAL ATTACK] Creating summary"

        if execution_id
          Attack::Execution.find(execution_id).update!(current_step: 3)
          ProgressHelper.broadcast_progress(
            progress_id: execution_id,
            percentage: 80,
            status: "サマリを作成中..."
          )
        end

        summary_cmd = [
          "python3",
          "-u",
          "auto-red-team-prompt/scripts/summary_safety_classification.py",
          "--input_file", evaluation_output_file.path,
          "--model_type", "vllm",
          "--model_config_file", config.file_path,
          "--num_max_samples", "-1",
          "--output_file", summary_output_file.path,
          "--log-format", "json"
        ]

        IO.popen(summary_cmd, err: [ :child, :out ]) do |io|
          io.each_line do |line|
            Rails.logger.info "Python output (summary): #{line.chomp}"
          end
        end

        # サマリ結果を読み込む
        summary_output_file.rewind
        summary_data = JSON.parse(summary_output_file.read)

        # 完了時に100%を送信
        if execution_id
          ProgressHelper.broadcast_progress(
            progress_id: execution_id,
            percentage: 100
          )
        end

        Rails.logger.info "[REAL ATTACK] Attack execution completed successfully"

        # 結果を返す
        {
          response: summary_data
        }
      ensure
        red_prompt_file.close
        red_prompt_file.unlink
        output_file.close
        output_file.unlink
        evaluation_output_file.close
        evaluation_output_file.unlink
        summary_output_file.close
        summary_output_file.unlink
      end

    rescue => e
      Rails.logger.error "Error executing attack: #{e.class}: #{e.message}"
      Rails.logger.error "Backtrace: #{e.backtrace.first(5).join("\n")}"

      {
        status: "error",
        message: "Error executing attack: #{e.message}",
        timestamp: Time.current.iso8601
      }
    end
  end
end
