module ExecutionHistory
  extend ActiveSupport::Concern

  included do
    # 状態管理
    enum :status, {
      pending: 0,
      running: 1,
      completed: 2,
      failed: 3
    }, default: :pending
  end

  class_methods do
    attr_accessor :client_class_name

    def client_class
      client_class_name.constantize
    end

    def ai_model_config
      client_class.config
    end

    def target_ai_model_config
      unless client_class.respond_to?(:target_config)
        raise NotImplementedError, "#{client_class_name} does not support target_config"
      end

      client_class.target_config
    end

    def statuses_i18n
      statuses.keys.index_with { |key| I18n.t("enums.status.#{key}") }
    end
  end

  def status_i18n
    I18n.t("enums.status.#{status}")
  end

  # 実行時間を計算
  def execution_time
    return nil unless started_at && (completed_at || failed_at)
    ((completed_at || failed_at) - started_at).round(2)
  end

  private

  # 実行開始
  def start!
    unless pending?
      raise StandardError, "Cannot start with status: #{status}"
    end

    update!(
      status: :running,
      started_at: Time.current
    )
  end

  # 実行完了
  def complete!(**attributes)
    unless running?
      raise StandardError, "Cannot complete with status: #{status}"
    end

    update!(
      { status: :completed, completed_at: Time.current }.merge(attributes)
    )
  end

  # 実行失敗
  def fail!(error_or_message)
    unless pending? || running?
      raise StandardError, "Cannot fail with status: #{status}"
    end

    error_detail = if error_or_message.is_a?(Exception)
      "#{error_or_message.message}\n\n--- Backtrace ---\n#{error_or_message.backtrace.first(30).join("\n")}"
    else
      error_or_message
    end

    update!(
      status: :failed,
      error_detail: error_detail,
      failed_at: Time.current
    )
  end
end
