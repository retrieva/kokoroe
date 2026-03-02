class AddNameToDefenseTrainingDatasets < ActiveRecord::Migration[8.0]
  def change
    add_column :defense_training_datasets, :name, :string
  end
end
