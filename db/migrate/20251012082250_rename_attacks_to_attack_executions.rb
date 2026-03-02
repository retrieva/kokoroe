class RenameAttacksToAttackExecutions < ActiveRecord::Migration[8.0]
  def change
    rename_table :attacks, :attack_executions
  end
end
