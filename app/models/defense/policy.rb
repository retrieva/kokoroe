class Defense::Policy < ApplicationRecord
  include ExecutionHistory

  self.client_class_name = "Defense::ExtensionClient"

  # 関連
  belongs_to :source_policy, class_name: "Defense::Policy", optional: true
  belongs_to :attack_execution, class_name: "Attack::Execution", optional: true
  has_many :extended_policies, class_name: "Defense::Policy", foreign_key: :source_policy_id, dependent: :restrict_with_error
  has_many :training_datasets, class_name: "Defense::TrainingDataset", foreign_key: :defense_policy_id, dependent: :restrict_with_error

  validates :name, presence: true
  validates :contents, presence: true, if: :completed?
  after_save :update_cycle_updated_at, if: :completed?

  # contentsが配列形式であることを検証（完了時のみ）
  validate :contents_must_be_array, if: :completed?

  # コールバック
  before_destroy :check_not_running
  after_create_commit :enqueue_extension_job, if: :source_policy

  # スコープ
  scope :recent, -> { order(created_at: :desc) }
  scope :uncompleted, -> { where(status: [ :pending, :running ]) }
  scope :initial, -> { where(source_policy_id: nil) }
  scope :extended, -> { where.not(source_policy_id: nil) }

  # 学習データのデフォルト名
  def default_training_dataset_name
    "#{name}による学習データ"
  end

  ESTIMATED_MINUTES_PER_CATEGORY_FOR_TRAINING_DATASET = 8

  def estimated_training_dataset_time
    return nil if attack_execution&.prompt_set&.scenario.nil? || attack_execution.prompt_set.scenario.details.size <= 0
    "最大約#{attack_execution.prompt_set.scenario.details.size * ESTIMATED_MINUTES_PER_CATEGORY_FOR_TRAINING_DATASET}分"
  end

  # 削除可能かどうか
  def deletable?
    return false if pending? || running?
    if initial?
      extended_policies.empty?
    else
      training_datasets.empty?
    end
  end

  # 削除できない理由
  def undeletable_reason
    return "実行中のため削除できません。" if pending? || running?
    if initial?
      return "拡張された防衛方針があるため削除できません。" if extended_policies.exists?
    else
      return "学習データがあるため削除できません。" if training_datasets.exists?
    end
    nil
  end

  # 初期方針かどうか（拡張されたものではない）
  def initial?
    source_policy.nil?
  end


  # 拡張実行
  def execute!
    raise "no source_policy" unless source_policy

    # 既に実行中や完了済みの場合はスキップ
    return unless pending?

    begin
      start!
      update!(request_body: build_request_body)
      broadcast_extension_content

      result = Defense::ExtensionClient.extend_policy(
        source_policy: source_policy,
        attack_execution: attack_execution
      )

      update!(contents: result[:contents])
      complete!(response_body: result[:response])
      Rails.logger.info "[DefenseExtensionJob] Policy ##{id} extension completed successfully"

      broadcast_extension_content
    rescue StandardError => e
      fail!(e)
      broadcast_extension_content

      Rails.logger.error "[DefenseExtensionJob] Policy ##{id} extension failed: #{e.message}"
      Rails.logger.error e.backtrace.join("\n")

      raise
    end
  end

  private

  def check_not_running
    return true unless pending? || running?

    errors.add(:base, "実行中のため削除できません。")
    throw :abort
  end

  def contents_must_be_array
    unless contents.is_a?(Array)
      errors.add(:contents, "must be an array")
    end
  end

  def update_cycle_updated_at
    update_column(:cycle_updated_at, updated_at)
    attack_execution&.update_column(:cycle_updated_at, updated_at)
    attack_execution&.prompt_set&.update_column(:cycle_updated_at, updated_at)
    attack_execution&.prompt_set&.scenario&.update_column(:cycle_updated_at, updated_at)
  end

  def build_request_body
    {
      source_policy: source_policy.contents,
      attack_execution: attack_execution.as_json
    }
  end

  def enqueue_extension_job
    DefenseExtensionJob.perform_later(id)
  end

  def broadcast_extension_content
    # 完了時は data_content、それ以外は extension_content を更新
    if completed?
      Turbo::StreamsChannel.broadcast_replace_to(
        "policy_#{id}",
        target: "policy_content_#{id}",
        partial: "defense/policies/data_content",
        locals: { policy: self }
      )
      # Flashメッセージを更新
      Turbo::StreamsChannel.broadcast_replace_to(
        "policy_#{id}",
        target: "flash-messages",
        partial: "shared/flash",
        locals: { notice_message: "防衛方針の拡張が完了しました。" }
      )
    else
      Turbo::StreamsChannel.broadcast_replace_to(
        "extension_#{id}",
        target: "extension_content_#{id}",
        partial: "defense/policies/extension_content",
        locals: { policy: self }
      )
    end
  end
end
