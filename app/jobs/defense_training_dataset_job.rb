class DefenseTrainingDatasetJob < ApplicationJob
  queue_as :default

  def perform(dataset_id)
    self.result_record = Defense::TrainingDataset.find(dataset_id)
    execute!
  end
end
