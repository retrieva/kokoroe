class CreateAttackScenarios < ActiveRecord::Migration[8.0]
  def change
    create_table :attack_scenarios do |t|
      t.string :name, null: false

      t.timestamps
    end
  end
end
