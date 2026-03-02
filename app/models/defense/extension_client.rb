require "json"
require "tempfile"

class Defense::ExtensionClient
  # テスト用: 次のリクエストを失敗させるフラグ
  cattr_accessor :force_next_failure
  self.force_next_failure = false

  def self.extend_policy(source_policy:, attack_execution:)
    if use_dummy?
      call_dummy_extension(source_policy: source_policy, attack_execution: attack_execution)
    else
      call_real_extension(source_policy: source_policy, attack_execution: attack_execution)
    end
  end

  private

  def self.use_dummy?
    ENV["USE_DUMMY_DEFENSE"] == "true"
  end

  def self.call_dummy_extension(source_policy:, attack_execution:)
    # テスト用: 強制失敗フラグのチェック
    if force_next_failure
      self.force_next_failure = false
      raise StandardError, "Forced failure for testing"
    end

    Rails.logger.info "[DUMMY DEFENSE EXTENSION] Starting dummy extension"
    Rails.logger.info "[DUMMY DEFENSE EXTENSION] Source policy: #{source_policy.contents.size} items"
    Rails.logger.info "[DUMMY DEFENSE EXTENSION] Attack execution: ##{attack_execution.id}"

    sleep(1) # シミュレート

    # ダミーの拡張された防衛方針を返す
    {
      contents: source_policy.contents + [
        "攻撃 ##{attack_execution.id} の結果を反映した新しい防衛方針",
        "脆弱性カテゴリ: #{dummy_categories.join(", ")} に対する追加の防衛策"
      ],
      response: {
        "summary" => "ダミーの脆弱性サマリー",
        "vulnerabilities" => dummy_vulnerabilities,
        "timestamp" => Time.current.iso8601
      }
    }
  end

  def self.dummy_categories
    [ "Hate/Hate-Speech", "Deception/Fraud", "Privacy/Sensitive-Data" ]
  end

  def self.dummy_vulnerabilities
    {
      "Hate/Hate-Speech" => {
        "success_rate" => 0.4,
        "description" => "ヘイトスピーチに関する脆弱性が検出されました"
      },
      "Deception/Fraud" => {
        "success_rate" => 0.3,
        "description" => "詐欺的な内容に対する防御が不十分です"
      }
    }
  end

  def self.config
    AiModelConfig::EVALUATION_LLM
  end

  def self.call_real_extension(source_policy:, attack_execution:)
    Rails.logger.info "[REAL DEFENSE EXTENSION] Starting real extension"
    Rails.logger.info "[REAL DEFENSE EXTENSION] Source policy ID: #{source_policy.id}"
    Rails.logger.info "[REAL DEFENSE EXTENSION] Attack execution ID: #{attack_execution.id}"

    # Python3の存在確認
    python_available = system("which python3 > /dev/null 2>&1")
    unless python_available
      Rails.logger.error "Error: python3 command not found"
      raise StandardError, "python3 command not found"
    end

    begin
      # 一時ファイルの準備
      input_data_file = Tempfile.new([ "defense_input", ".json" ])
      constitution_output_file = Tempfile.new([ "constitution_output", ".json" ])
      summary_output_file = Tempfile.new([ "summary_output", ".json" ])

      # 入力データの準備（Pythonスクリプトが期待する形式）
      # 攻撃実行結果から必要なデータを取得
      attack_response = attack_execution.response_body || {}
      response_data = attack_response["response"] || {}

      # 攻撃シナリオ情報を準備（カテゴリごとにグループ化）
      attack_scenario_data = []
      if attack_execution.prompt_set
        # プロンプトをカテゴリーごとにグループ化
        grouped_prompts = attack_execution.prompt_set.prompts.group_by(&:category)
        grouped_prompts.each do |category, prompts|
          attack_scenario_data << {
            "category" => category,
            "description" => category, # カテゴリ名を説明として使用
            "examples" => prompts.map(&:text),
            "severity" => 3 # デフォルト値
          }
        end
      end

      input_data = {
        "attack-scenario" => attack_scenario_data,
        "quantitative-summary" => response_data["quantitative-summary"] || {},
        "qualitative-summary" => response_data["qualitative-summary"] || {},
        "llm-constitutions" => source_policy.contents
      }

      input_data_file.write(JSON.pretty_generate(input_data))
      input_data_file.flush

      Rails.logger.debug "[REAL DEFENSE EXTENSION] Input data prepared: #{source_policy.contents.size} constitution items, #{attack_scenario_data.size} scenario categories"

      # Python スクリプトの実行
      cmd = [
        "python3",
        "-u",
        "auto-red-team-prompt/scripts/blue-teaming/run_pre_process.py",
        "--model_type", "vllm",
        "--model_config_file", config.file_path,
        "--input_data", input_data_file.path,
        "--constitution_output_path", constitution_output_file.path,
        "--summary_output_path", summary_output_file.path
      ]

      Rails.logger.info "[REAL DEFENSE EXTENSION] Executing: #{cmd.join(' ')}"

      exit_status = nil
      IO.popen(cmd, err: [ :child, :out ]) do |io|
        io.each_line do |line|
          Rails.logger.info "Python output: #{line.chomp}"
        end
        io.close
        exit_status = $?.exitstatus
      end

      Rails.logger.info "[REAL DEFENSE EXTENSION] Python script exited with status: #{exit_status}"

      # 実行結果の読み込み
      constitution_output_file.rewind
      summary_output_file.rewind

      constitution_content = constitution_output_file.read
      summary_content = summary_output_file.read

      Rails.logger.debug "[REAL DEFENSE EXTENSION] Constitution output size: #{constitution_content.bytesize} bytes"
      Rails.logger.debug "[REAL DEFENSE EXTENSION] Summary output size: #{summary_content.bytesize} bytes"

      if constitution_content.empty?
        raise StandardError, "Constitution output file is empty. Python script exited with status: #{exit_status}"
      end

      if summary_content.empty?
        raise StandardError, "Summary output file is empty. Python script exited with status: #{exit_status}"
      end

      new_constitution = JSON.parse(constitution_content)
      summary = JSON.parse(summary_content)

      Rails.logger.info "[REAL DEFENSE EXTENSION] Constitution parsed: #{new_constitution.class}"
      Rails.logger.debug "[REAL DEFENSE EXTENSION] Constitution content: #{new_constitution.inspect}"
      Rails.logger.debug "[REAL DEFENSE EXTENSION] Summary content: #{summary.inspect}"

      # Constitutionが配列でない場合、配列に変換を試みる
      constitution_array = if new_constitution.is_a?(Array)
        new_constitution
      elsif new_constitution.is_a?(Hash) && new_constitution["texts"]
        new_constitution["texts"]
      elsif new_constitution.is_a?(Hash) && new_constitution["constitutions"]
        new_constitution["constitutions"]
      elsif new_constitution.is_a?(Hash) && new_constitution["llm-constitutions"]
        new_constitution["llm-constitutions"]
      else
        raise StandardError, "Unexpected constitution format: #{new_constitution.class}. Content: #{new_constitution.inspect[0..200]}"
      end

      Rails.logger.info "[REAL DEFENSE EXTENSION] Extension completed successfully with #{constitution_array.size} constitution items"

      {
        contents: constitution_array,
        response: (summary.is_a?(Hash) ? summary : {}).merge(
          "python_exit_status" => exit_status,
          "execution_info" => {
            "constitution_size" => constitution_array.size,
            "timestamp" => Time.current.iso8601
          }
        )
      }
    ensure
      # 一時ファイルのクリーンアップ
      input_data_file&.close
      input_data_file&.unlink
      constitution_output_file&.close
      constitution_output_file&.unlink
      summary_output_file&.close
      summary_output_file&.unlink
    end
  end
end
