class AttackPromptSetGenerationJob < ApplicationJob
  queue_as :default

  def perform(prompt_set_id)
    self.result_record = Attack::PromptSet.find(prompt_set_id)
    execute!
  end
end
