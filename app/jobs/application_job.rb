class ApplicationJob < ActiveJob::Base
  # Automatically retry jobs that encountered a deadlock
  # retry_on ActiveRecord::Deadlocked

  # Most jobs are safe to ignore if the underlying records are no longer available
  # discard_on ActiveJob::DeserializationError

  attr_accessor :result_record

  rescue_from StandardError do |exception|
    ExceptionNotifier.notify_exception(exception, data: { job: self.class.name })
    raise
  end

  private

  def execute!
    result_record.execute!
    if result_record.failed? # 通知忘れ時も failed なら通知させる
      raise "Job failure detected: #{result_record.error_detail}"
    end
  end
end
