class AttackExecutionJob < ApplicationJob
  queue_as :default

  def perform(execution_id)
    self.result_record = Attack::Execution.find(execution_id)
    execute!
  end
end
