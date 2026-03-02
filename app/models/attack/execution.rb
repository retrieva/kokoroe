class Attack::Execution < ApplicationRecord
  include ExecutionHistory

  self.table_name = "attack_executions"
  self.client_class_name = "Attack::ExecutionClient"

  belongs_to :prompt_set, class_name: "Attack::PromptSet", foreign_key: :attack_prompt_set_id, inverse_of: :executions
  has_many :defense_policies, class_name: "Defense::Policy", foreign_key: :attack_execution_id, dependent: :nullify

  # コールバック
  after_create_commit :enqueue_execution_job
  after_update_commit :broadcast_update
  after_save :update_cycle_updated_at

  # バリデーション
  validates :name, presence: true
  validates :status, presence: true

  # スコープ
  scope :recent, -> { order(created_at: :desc) }
  scope :uncompleted, -> { where(status: [ :pending, :running ]) }
  scope :with_prompt_set, -> { includes(:prompt_set) }

  # 防衛方針のデフォルト名
  def default_policy_name
    "#{name}への防衛方針"
  end

  def estimated_extension_time
    "1分未満"
  end

  # 削除可能かどうか
  def deletable?
    return false if pending? || running?
    defense_policies.empty?
  end

  # 削除できない理由
  def undeletable_reason
    return "実行中のため削除できません。" if pending? || running?
    return "拡張された防衛方針があるため削除できません。" if defense_policies.exists?
    nil
  end

  def execute!
    # 既に実行中や完了済みの場合はスキップ
    return unless pending?

    begin
      # 実行開始
      start!

      # プロンプト集からリクエストボディを生成して保存
      request_body = prompt_set.prompts.map do |prompt|
        {
          category: prompt.category,
          text: prompt.text
        }
      end
      update!(request_body: request_body)
      broadcast_execution_content
      sleep 1 # ブロードキャストがブラウザに届くのを待つ

      # Attack::ExecutionClientを呼び出して攻撃を実行
      response = Attack::ExecutionClient.call_attack(request_body, execution_id: id)

      # エラーレスポンスの場合は失敗扱い
      if response[:status] == "error"
        fail!(response[:message])
        broadcast_execution_content
        Rails.logger.error "[AttackExecutionJob] Execution ##{id} failed: #{response[:message]}"
        return
      end

      # 実行完了
      complete!(response_body: response)

      # 実行コンテンツ全体を更新
      broadcast_execution_content

      Rails.logger.info "[AttackExecutionJob] Execution ##{id} completed successfully"
    rescue StandardError => e
      # 実行失敗
      fail!(e)
      broadcast_execution_content

      Rails.logger.error "[AttackExecutionJob] Execution ##{id} failed: #{e.message}"
      Rails.logger.error e.backtrace.join("\n")

      raise
    end
  end

  private

  def enqueue_execution_job
    AttackExecutionJob.perform_later(id)
  end

  def broadcast_execution_content
    # 完了時は data_content、それ以外は execution_content を更新
    if completed?
      initial_policies = Defense::Policy.initial.completed.recent
      Turbo::StreamsChannel.broadcast_replace_to(
        "attack_report_#{id}",
        target: "report_content_#{id}",
        partial: "attack/reports/data_content",
        locals: { execution: self, initial_policies: initial_policies }
      )
      # 改善サイクルも更新（拡張ボタンを表示するため）
      Turbo::StreamsChannel.broadcast_replace_to(
        "attack_report_#{id}",
        target: "report_improvement_cycle_#{id}",
        partial: "attack/reports/improvement_cycle",
        locals: { execution: self, initial_policies: initial_policies }
      )
      # Flashメッセージを更新
      Turbo::StreamsChannel.broadcast_replace_to(
        "attack_report_#{id}",
        target: "flash-messages",
        partial: "shared/flash",
        locals: { notice_message: "攻撃の実行が完了しました。" }
      )
    else
      Turbo::StreamsChannel.broadcast_replace_to(
        "progress_#{id}",
        target: "execution_content_#{id}",
        partial: "attack/reports/execution_content",
        locals: { execution: self }
      )
    end
  end

  def broadcast_update
    broadcast_replace_to(
      "attack_execution_#{id}",
      target: "attack_execution_status",
      partial: "attack/reports/status",
      locals: { execution: self }
    )
  end

  def update_cycle_updated_at
    update_column(:cycle_updated_at, updated_at)
    prompt_set&.update_column(:cycle_updated_at, updated_at)
    prompt_set&.scenario&.update_column(:cycle_updated_at, updated_at)
  end
end
