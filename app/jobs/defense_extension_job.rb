class DefenseExtensionJob < ApplicationJob
  queue_as :default

  def perform(policy_id)
    self.result_record = Defense::Policy.find(policy_id)
    raise "no source_policy" unless result_record.source_policy

    execute!
  end
end
