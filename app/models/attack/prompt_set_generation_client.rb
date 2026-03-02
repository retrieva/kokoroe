require "json"
require "tempfile"

class Attack::PromptSetGenerationClient
  # テスト用: 次のリクエストを失敗させるフラグ
  cattr_accessor :force_next_failure
  self.force_next_failure = false

  def self.call_prompt_generation(scenario_hash, prompt_set_id: nil)
    if use_dummy?
      call_dummy_prompt_generation(scenario_hash, prompt_set_id: prompt_set_id)
    else
      call_real_prompt_generation(scenario_hash, prompt_set_id: prompt_set_id)
    end
  end

  private

  def self.use_dummy?
    ENV["USE_DUMMY_ATTACK"] == "true"
  end

  def self.call_dummy_prompt_generation(scenario_hash, prompt_set_id: nil)
    # テスト用: 強制失敗フラグのチェック
    if force_next_failure
      self.force_next_failure = false # フラグをリセット
      raise StandardError, "Forced failure for testing"
    end

    # ダミー実行のログ出力
    Rails.logger.info "[DUMMY PROMPT GENERATION] Starting dummy prompt generation"
    Rails.logger.info "[DUMMY PROMPT GENERATION] Scenario: #{scenario_hash}"

    # 開始日時を更新
    if prompt_set_id
      prompt_set = Attack::PromptSet.find(prompt_set_id)
      ProgressHelper.broadcast_started_at(
        progress_id: prompt_set_id,
        started_at: prompt_set.started_at
      )
    end

    # 処理時間のシミュレート（1秒ごとに10%進捗）
    10.times do |i|
      percentage = (i + 1) * 10
      status = case percentage
      when 0..30 then "シナリオを分析中..."
      when 31..60 then "プロンプトを生成中..."
      when 61..100 then "生成結果を検証中..."
      end

      # 進捗を送信
      if prompt_set_id
        ProgressHelper.broadcast_progress(
          progress_id: prompt_set_id,
          percentage: percentage,
          status: status
        )
      end

      sleep(Attack::DummyClientConfig.progress_sleep_duration)
    end

    # scenario_hashはdetailsの配列
    # ダミーのプロンプト集レスポンスを返す
    {
      prompts: scenario_hash.flat_map do |detail|
        category = detail["category"]
        description = detail["description"]

        # 各カテゴリに対して3つのプロンプトを生成
        [
          {
            category: category,
            text: "#{description}に関する攻撃プロンプト1"
          },
          {
            category: category,
            text: "#{description}に関する攻撃プロンプト2"
          },
          {
            category: category,
            text: "#{description}に関する攻撃プロンプト3"
          }
        ]
      end
    }
  end

  def self.config
    AiModelConfig::EVALUATION_LLM
  end

  def self.call_real_prompt_generation(scenario_hash, prompt_set_id: nil)
    # 本番の外部システム呼び出し
    Rails.logger.info "[REAL PROMPT GENERATION] Calling external prompt generation system"
    Rails.logger.info "[REAL PROMPT GENERATION] Scenario: #{scenario_hash}"

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
      # scenario_hashを一時ファイルとして保存
      risk_file = Tempfile.new([ "risk", ".json" ])
      output_file = Tempfile.new([ "output", ".json" ])

      begin
        # scenario_hashをrisk JSONフォーマットに変換
        # Pythonスクリプトが期待するフォーマット: { "attack-scenario": [...] }
        risk_data = {
          "attack-scenario": scenario_hash.map do |detail|
            {
              category: detail["category"],
              description: detail["description"],
              examples: detail["examples"] || [],
              severity: detail["severity"] || 3
            }
          end
        }
        risk_file.write(JSON.pretty_generate(risk_data))
        risk_file.flush

        # 開始日時を更新
        if prompt_set_id
          prompt_set = Attack::PromptSet.find(prompt_set_id)
          ProgressHelper.broadcast_started_at(
            progress_id: prompt_set_id,
            started_at: prompt_set.started_at
          )
        end

        # Pythonスクリプトを実行
        cmd = [
          "python3",
          "-u",
          "auto-red-team-prompt/scripts/run_generate_red_prompt.py",
          "--progress_report",
          "--model_type", "vllm",
          "--model_config_file", config.file_path,
          "--risk_json", risk_file.path,
          "--output_path", output_file.path,
          "--log-level", "INFO"
        ]

        IO.popen(cmd, err: [ :child, :out ]) do |io|
          io.each_line do |line|
            begin
              data = JSON.parse(line)
              # JSON形式の進捗データの場合
              if data["progress_percentage"]
                Rails.logger.info "Progress: #{data["progress_percentage"]}% - #{data["status"]}"

                # 進捗を送信
                if prompt_set_id
                  ProgressHelper.broadcast_progress(
                    progress_id: prompt_set_id,
                    percentage: data["progress_percentage"],
                    status: data["status"]
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

        # 実行結果を読み込む
        output_file.rewind
        result_data = JSON.parse(output_file.read)

        # 完了時に100%を送信
        if prompt_set_id
          ProgressHelper.broadcast_progress(
            progress_id: prompt_set_id,
            percentage: 100
          )
        end

        Rails.logger.info "Python script completed successfully"
        Rails.logger.info "Result data keys: #{result_data.keys.inspect}"

        # 結果をフォーマットして返す
        # Pythonスクリプトの出力はカテゴリごとにグループ化されているため、フラット化する
        # { "カテゴリ1" => [prompt1, prompt2, ...], "カテゴリ2" => [...] }
        # を { prompts: [prompt1, prompt2, ...] } に変換
        all_prompts = result_data.values.flatten
        Rails.logger.info "Total prompts: #{all_prompts.size}"

        {
          prompts: all_prompts.map do |prompt|
            {
              category: prompt["category"],
              text: prompt["prompt"]
            }
          end
        }
      ensure
        risk_file.close
        risk_file.unlink
        output_file.close
        output_file.unlink
      end

    rescue => e
      Rails.logger.error "Error executing Python script: #{e.class}: #{e.message}"
      Rails.logger.error "Backtrace: #{e.backtrace.first(5).join("\n")}"

      {
        status: "error",
        message: "Error executing prompt generation: #{e.message}",
        timestamp: Time.current.iso8601
      }
    end
  end
end
