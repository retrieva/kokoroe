class AddCurrentStepToAttackExecutions < ActiveRecord::Migration[8.0]
  def change
    add_column :attack_executions, :current_step, :integer
  end
end
