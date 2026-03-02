class AddNameToAttackExecutions < ActiveRecord::Migration[8.0]
  def change
    add_column :attack_executions, :name, :string, null: false, default: ""
  end
end
