class AddCurrentStepToDefenseTrainingDatasets < ActiveRecord::Migration[8.0]
  def change
    add_column :defense_training_datasets, :current_step, :integer, default: 0
  end
end
