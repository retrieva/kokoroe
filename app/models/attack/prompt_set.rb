class Attack::PromptSet < ApplicationRecord
  include ExecutionHistory

  self.client_class_name = "Attack::PromptSetGenerationClient"

  belongs_to :scenario, class_name: "Attack::Scenario", foreign_key: :attack_scenario_id, optional: true
  has_many :prompts, class_name: "Attack::Prompt", foreign_key: :attack_prompt_set_id, dependent: :destroy, inverse_of: :prompt_set
  has_many :executions, class_name: "Attack::Execution", foreign_key: :attack_prompt_set_id, dependent: :destroy, inverse_of: :prompt_set

  validates :name, presence: true
  validates :status, presence: true

  scope :recent, -> { order(created_at: :desc) }
  scope :uncompleted, -> { where(status: [ :pending, :running ]) }

  ESTIMATED_MINUTES_PER_CATEGORY_FOR_ATTACK_EXECUTION = 6

  # 攻撃結果レポートのデフォルト名
  def default_execution_name
    "#{name}による攻撃"
  end

  def estimated_execution_time
    return nil if scenario.nil? || scenario.details.size <= 0
    "最大約#{scenario.details.size * ESTIMATED_MINUTES_PER_CATEGORY_FOR_ATTACK_EXECUTION}分"
  end

  # 削除可能かどうか
  def deletable?
    return false if pending? || running?
    executions.empty?
  end

  # 削除できない理由
  def undeletable_reason
    return "実行中のため削除できません。" if pending? || running?
    return "攻撃結果レポートがあるため削除できません。" if executions.exists?
    nil
  end

  after_create_commit :enqueue_generation_job
  after_save :update_cycle_updated_at

  # プロンプト集生成を実行
  def execute!
    # 既に実行中や完了済みの場合はスキップ
    return unless pending?

    begin
      # 実行開始
      start!

      # シナリオからリクエストボディを生成して保存
      request_body = scenario.as_json
      update!(request_body: request_body)
      broadcast_generation_content

      # Attack::PromptSetGenerationClientを呼び出してプロンプト集を生成
      response = Attack::PromptSetGenerationClient.call_prompt_generation(request_body, prompt_set_id: id)

      # エラーレスポンスの場合は失敗扱い
      if response[:status] == "error"
        fail!(response[:message])
        broadcast_generation_content
        Rails.logger.error "[PromptSet] Generation ##{id} failed: #{response[:message]}"
        return
      end

      # プロンプトを作成
      build_prompts(response)
      save!

      # 実行完了
      complete!(response_body: response)

      # 生成コンテンツ全体を更新
      broadcast_generation_content

      Rails.logger.info "[PromptSet] Generation ##{id} completed successfully"
    rescue StandardError => e
      # 実行失敗
      fail!(e)
      broadcast_generation_content

      Rails.logger.error "[PromptSet] Generation ##{id} failed: #{e.message}"
      Rails.logger.error e.backtrace.join("\n")

      raise
    end
  end

  # プロンプトデータからPromptレコードを作成
  def build_prompts(response)
    return unless response.is_a?(Hash)

    # responseが { prompts: [...] } の形式の場合
    prompts_data = response[:prompts] || response["prompts"]
    return unless prompts_data.is_a?(Array)

    prompts_data.each_with_index do |prompt_hash, index|
      prompts.build(
        category: prompt_hash[:category] || prompt_hash["category"],
        text: prompt_hash[:text] || prompt_hash["text"],
        position: index + 1,
        raw_data: prompt_hash
      )
    end
  end

  # カテゴリごとにグループ化されたプロンプトを取得
  def categorized_prompts
    prompts.order(:position, :id).group_by(&:category)
  end

  private

  def enqueue_generation_job
    AttackPromptSetGenerationJob.perform_later(id)
  end

  def update_cycle_updated_at
    update_column(:cycle_updated_at, updated_at)
    scenario&.update_column(:cycle_updated_at, updated_at)
  end

  def broadcast_generation_content
    # 完了時は data_content、それ以外は generation_content を更新
    if completed?
      Turbo::StreamsChannel.broadcast_replace_to(
        "prompt_set_#{id}",
        target: "prompt_set_content_#{id}",
        partial: "attack/prompt_sets/data_content",
        locals: { prompt_set: self }
      )
      # 改善サイクルも更新（攻撃ボタンを表示するため）
      Turbo::StreamsChannel.broadcast_replace_to(
        "prompt_set_#{id}",
        target: "prompt_set_improvement_cycle_#{id}",
        partial: "attack/prompt_sets/improvement_cycle",
        locals: { prompt_set: self }
      )
      # Flashメッセージを更新
      Turbo::StreamsChannel.broadcast_replace_to(
        "prompt_set_#{id}",
        target: "flash-messages",
        partial: "shared/flash",
        locals: { notice_message: "プロンプト集の生成が完了しました。" }
      )
    else
      Turbo::StreamsChannel.broadcast_replace_to(
        "progress_#{id}",
        target: "generation_content_#{id}",
        partial: "attack/prompt_sets/generation_content",
        locals: { prompt_set: self }
      )
    end
  end
end
