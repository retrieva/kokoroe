class Defense::TrainingDataset < ApplicationRecord
  include ExecutionHistory

  self.client_class_name = "Defense::TrainingDatasetClient"

  # 関連
  belongs_to :policy, class_name: "Defense::Policy", foreign_key: :defense_policy_id
  belongs_to :attack_execution, class_name: "Attack::Execution", foreign_key: :attack_execution_id

  # コールバック
  after_create_commit :enqueue_generation_job
  after_update_commit :broadcast_update
  after_save :update_cycle_updated_at

  # バリデーション
  validates :status, presence: true

  # スコープ
  scope :recent, -> { order(created_at: :desc) }
  scope :uncompleted, -> { where(status: [ :pending, :running ]) }

  # 削除可能かどうか
  def deletable?
    return false if pending? || running?
    true
  end

  # 削除できない理由
  def undeletable_reason
    return "実行中のため削除できません。" if pending? || running?
    nil
  end

  # 学習データ生成を実行
  def execute!
    # 既に実行中や完了済みの場合はスキップ
    return unless pending?

    begin
      start!
      broadcast_update

      # Defense::TrainingDatasetClientを呼び出して学習データを生成
      result = Defense::TrainingDatasetClient.generate_training_data(
        dataset: self,
        policy: policy,
        attack_execution: attack_execution
      )

      # 実行完了
      complete!(
        sft_data_path: result[:sft_data_path],
        dpo_data_path: result[:dpo_data_path],
        report_path: result[:report_path],
        report_body: result[:report]
      )

      broadcast_update

      Rails.logger.info "[DefenseTrainingDatasetJob] Dataset ##{id} completed successfully"
    rescue StandardError => e
      fail!(e)
      broadcast_update

      Rails.logger.error "[DefenseTrainingDatasetJob] Dataset ##{id} failed: #{e.message}"
      Rails.logger.error e.backtrace.join("\n")

      raise
    end
  end

  private

  def enqueue_generation_job
    DefenseTrainingDatasetJob.perform_later(id)
  end

  def broadcast_update
    if completed?
      # 完了時はコンテンツ全体を更新
      Turbo::StreamsChannel.broadcast_replace_to(
        "training_dataset_#{id}",
        target: "training_dataset_content_#{id}",
        partial: "defense/training_datasets/data_content",
        locals: { dataset: self }
      )
      # Flashメッセージを更新
      Turbo::StreamsChannel.broadcast_replace_to(
        "training_dataset_#{id}",
        target: "flash-messages",
        partial: "shared/flash",
        locals: { notice_message: "学習データの生成が完了しました。" }
      )
    else
      # 実行中・失敗時はステータス部分のみ更新
      broadcast_replace_to(
        "training_dataset_#{id}",
        target: "training_dataset_status",
        partial: "defense/training_datasets/status",
        locals: { dataset: self }
      )
    end
  end

  def update_cycle_updated_at
    update_column(:cycle_updated_at, updated_at)
    policy&.update_column(:cycle_updated_at, updated_at)
    policy&.attack_execution&.update_column(:cycle_updated_at, updated_at)
    policy&.attack_execution&.prompt_set&.update_column(:cycle_updated_at, updated_at)
    policy&.attack_execution&.prompt_set&.scenario&.update_column(:cycle_updated_at, updated_at)
  end
end
