class AddCycleUpdatedAtToModels < ActiveRecord::Migration[8.0]
  def change
    add_column :attack_scenarios, :cycle_updated_at, :datetime
    add_column :attack_prompt_sets, :cycle_updated_at, :datetime
    add_column :attack_executions, :cycle_updated_at, :datetime
    add_column :defense_policies, :cycle_updated_at, :datetime
    add_column :defense_training_datasets, :cycle_updated_at, :datetime
  end
end
