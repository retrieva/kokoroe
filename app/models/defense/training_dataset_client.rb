require "json"
require "tempfile"
require "fileutils"

class Defense::TrainingDatasetClient
  def self.config
    AiModelConfig::EVALUATION_LLM
  end

  def self.target_config
    Rails.env.production? ? AiModelConfig::TARGET_LLM_PRODUCTION : AiModelConfig::TARGET_LLM_DEVELOPMENT
  end

  def self.generate_training_data(dataset:, policy:, attack_execution:)
    Rails.logger.info "[TRAINING DATASET] Starting generation"
    Rails.logger.info "[TRAINING DATASET] Policy ID: #{policy.id}"
    Rails.logger.info "[TRAINING DATASET] Attack execution: #{attack_execution.id}"

    # Python3の存在確認
    python_available = system("which python3 > /dev/null 2>&1")
    unless python_available
      Rails.logger.error "Error: python3 command not found"
      raise StandardError, "python3 command not found"
    end

    # 出力ディレクトリの準備
    timestamp = Time.current.to_i
    output_dir = Rails.root.join("tmp", "training_datasets", "dataset_#{timestamp}")
    FileUtils.mkdir_p(output_dir)

    begin
      # ステップ1: 攻撃プロンプト生成
      dataset.update!(current_step: 1)
      red_prompt_path = generate_red_prompts(
        policy: policy,
        attack_execution: attack_execution,
        output_dir: output_dir
      )
      dataset.update!(red_prompt_path: red_prompt_path)

      # ステップ2: 応答生成
      dataset.update!(current_step: 2)
      response_path = generate_responses(
        red_prompt_path: red_prompt_path,
        output_dir: output_dir
      )
      dataset.update!(response_path: response_path)

      # ステップ3: 応答修正
      dataset.update!(current_step: 3)
      corrected_response_path = correct_responses(
        policy: policy,
        response_path: response_path,
        output_dir: output_dir
      )
      dataset.update!(corrected_response_path: corrected_response_path)

      # ステップ4: 学習データ保存
      dataset.update!(current_step: 4)
      result = save_training_data(
        policy: policy,
        attack_execution: attack_execution,
        corrected_response_path: corrected_response_path,
        output_dir: output_dir
      )

      Rails.logger.info "[TRAINING DATASET] Generation completed successfully"
      result
    rescue StandardError => e
      Rails.logger.error "[TRAINING DATASET] Generation failed: #{e.message}"
      raise
    end
  end

  private

  # ステップ1: 攻撃プロンプト生成
  def self.generate_red_prompts(policy:, attack_execution:, output_dir:)
    Rails.logger.info "[TRAINING DATASET] Step 1: Generating red prompts"

    # 入力データの準備
    risk_data_file = Tempfile.new([ "risk_data", ".json" ])
    vulnerability_summary_file = Tempfile.new([ "vulnerability_summary", ".json" ])
    output_file = output_dir.join("red_prompt.json")

    # 攻撃シナリオデータの準備
    if attack_execution.prompt_set
      grouped_prompts = attack_execution.prompt_set.prompts.group_by(&:category)
      attack_scenarios = grouped_prompts.map do |category, prompts|
        {
          "category" => category,
          "description" => category,
          "examples" => prompts.map(&:text),
          "severity" => 3
        }
      end
    else
      # デフォルトのリスクデータ
      attack_scenarios = [
        {
          "category" => "General",
          "description" => "一般的なリスク",
          "examples" => [ "テスト用プロンプト" ],
          "severity" => 3
        }
      ]
    end

    risk_data = { "attack-scenario" => attack_scenarios }
    risk_data_file.write(JSON.pretty_generate(risk_data))
    risk_data_file.flush

    # vulnerability_summaryの準備（Pythonスクリプトが期待する形式に変換）
    attack_response = attack_execution.response_body || {}
    response_data = attack_response["response"] || {}
    quantitative_summary = response_data["quantitative-summary"] || {}

    # Pythonスクリプトが期待する形式に変換
    # 変換前 (quantitative_summary):
    #   { "カテゴリ名" => { "number-of-successes" => 10, "number-of-attacks" => 20, "success-rate" => 0.5 } }
    # 変換後 (vulnerability_summary):
    #   { "カテゴリ名" => { "vulnerability_stats" => { "number_of_successes" => 10, ... }, "severity" => 3 } }
    vulnerability_summary = {}
    quantitative_summary.each do |category, stats|
      vulnerability_summary[category] = {
        "vulnerability_stats" => {
          "number_of_successes" => stats["number-of-successes"] || 0,
          "number_of_attacks" => stats["number-of-attacks"] || 0,
          "success_rate" => stats["success-rate"] || 0.0
        },
        "severity" => 3  # デフォルト値
      }
    end

    vulnerability_summary_file.write(JSON.pretty_generate(vulnerability_summary))
    vulnerability_summary_file.flush

    # Pythonスクリプト実行
    cmd = [
      "python3", "-u",
      "auto-red-team-prompt/scripts/blue-teaming/run_generate_red_prompt.py",
      "--model_type", "vllm",
      "--model_config_file", config.file_path,
      "--risk_json", risk_data_file.path,
      "--output_path", output_file.to_s,
      "--vulnerability_summary", vulnerability_summary_file.path
    ]

    execute_python_script(cmd, "Step 1: Red prompt generation")

    risk_data_file.close
    risk_data_file.unlink
    vulnerability_summary_file.close
    vulnerability_summary_file.unlink

    output_file.to_s
  end

  # ステップ2: 応答生成
  def self.generate_responses(red_prompt_path:, output_dir:)
    Rails.logger.info "[TRAINING DATASET] Step 2: Generating responses"

    output_file = output_dir.join("response.json")

    cmd = [
      "python3", "-u",
      "auto-red-team-prompt/scripts/run_generate_response.py",
      "--red_prompt_file", red_prompt_path,
      "--model_type", "vllm",
      "--model_config_file", target_config.file_path,
      "--output_file", output_file.to_s
    ]

    execute_python_script(cmd, "Step 2: Response generation")

    output_file.to_s
  end

  # ステップ3: 応答修正
  def self.correct_responses(policy:, response_path:, output_dir:)
    Rails.logger.info "[TRAINING DATASET] Step 3: Correcting responses"

    # Constitutionファイルの準備（Pythonスクリプトが期待する形式に変換）
    # 変換前 (policy.contents):
    #   ["ルール1", "ルール2", ...]
    # 変換後 (constitution_data):
    #   { "texts" => ["ルール1", "ルール2", ...] }
    constitution_file = Tempfile.new([ "constitution", ".json" ])
    constitution_data = { "texts" => policy.contents }
    constitution_file.write(JSON.pretty_generate(constitution_data))
    constitution_file.flush

    output_file = output_dir.join("corrected_response.json")

    cmd = [
      "python3", "-u",
      "auto-red-team-prompt/scripts/blue-teaming/run_generate_training_data.py",
      "--model_type", "vllm",
      "--model_config_file", config.file_path,
      "--constitution_file", constitution_file.path,
      "--generator_output_file", response_path,
      "--output_file", output_file.to_s
    ]

    execute_python_script(cmd, "Step 3: Response correction")

    constitution_file.close
    constitution_file.unlink

    output_file.to_s
  end

  # ステップ4: 学習データ保存
  def self.save_training_data(policy:, attack_execution:, corrected_response_path:, output_dir:)
    Rails.logger.info "[TRAINING DATASET] Step 4: Saving training data"

    # Constitutionファイルの準備（Pythonスクリプトが期待する形式に変換）
    # 変換前 (policy.contents):
    #   ["ルール1", "ルール2", ...]
    # 変換後 (constitution_data):
    #   { "texts" => ["ルール1", "ルール2", ...] }
    constitution_file = Tempfile.new([ "constitution", ".json" ])
    constitution_data = { "texts" => policy.contents }
    constitution_file.write(JSON.pretty_generate(constitution_data))
    constitution_file.flush

    # vulnerability_summaryファイルの準備（Pythonスクリプトが期待する形式に変換）
    vulnerability_summary_file = Tempfile.new([ "vulnerability_summary", ".json" ])
    attack_response = attack_execution.response_body || {}
    response_data = attack_response["response"] || {}
    quantitative_summary = response_data["quantitative-summary"] || {}

    # Pythonスクリプトが期待する形式に変換
    # 変換前 (quantitative_summary):
    #   { "カテゴリ名" => { "number-of-successes" => 10, "number-of-attacks" => 20, "success-rate" => 0.5 } }
    # 変換後 (vulnerability_summary):
    #   { "カテゴリ名" => { "vulnerability_stats" => { "number_of_successes" => 10, ... }, "severity" => 3 } }
    vulnerability_summary = {}
    quantitative_summary.each do |category, stats|
      vulnerability_summary[category] = {
        "vulnerability_stats" => {
          "number_of_successes" => stats["number-of-successes"] || 0,
          "number_of_attacks" => stats["number-of-attacks"] || 0,
          "success_rate" => stats["success-rate"] || 0.0
        },
        "severity" => 3  # デフォルト値
      }
    end

    vulnerability_summary_file.write(JSON.pretty_generate(vulnerability_summary))
    vulnerability_summary_file.flush

    sft_data_path = output_dir.join("sft_data.json")
    dpo_data_path = output_dir.join("dpo_data.json")
    report_path = output_dir.join("report.json")

    cmd = [
      "python3", "-u",
      "auto-red-team-prompt/scripts/blue-teaming/run_post_process.py",
      "--training_data_path", corrected_response_path,
      "--output_sft_data_path", sft_data_path.to_s,
      "--output_dpo_data_path", dpo_data_path.to_s,
      "--constitution_path", constitution_file.path,
      "--vulnerability_summary_path", vulnerability_summary_file.path,
      "--output_report_path", report_path.to_s
    ]

    execute_python_script(cmd, "Step 4: Post-process")

    constitution_file.close
    constitution_file.unlink
    vulnerability_summary_file.close
    vulnerability_summary_file.unlink

    # レポートの読み込み
    report_data = JSON.parse(File.read(report_path))

    {
      red_prompt_path: output_dir.join("red_prompt.json").to_s,
      response_path: output_dir.join("response.json").to_s,
      corrected_response_path: corrected_response_path,
      sft_data_path: sft_data_path.to_s,
      dpo_data_path: dpo_data_path.to_s,
      report_path: report_path.to_s,
      report: report_data
    }
  end

  # Pythonスクリプトの実行
  def self.execute_python_script(cmd, step_name)
    Rails.logger.info "[TRAINING DATASET] Executing: #{cmd.join(' ')}"

    exit_status = nil
    output_lines = []
    IO.popen(cmd, err: [ :child, :out ]) do |io|
      io.each_line do |line|
        Rails.logger.info "Python output: #{line.chomp}"
        output_lines << line.chomp
      end
      io.close
      exit_status = $?.exitstatus
    end

    Rails.logger.info "[TRAINING DATASET] #{step_name} exited with status: #{exit_status}"

    unless exit_status == 0
      error_output = output_lines.last(50).join("\n")
      raise StandardError, "#{step_name} failed with exit status: #{exit_status}\n\n--- Python Output ---\n#{error_output}"
    end
  end
end
