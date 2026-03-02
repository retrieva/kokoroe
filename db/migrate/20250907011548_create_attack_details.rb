class CreateAttackDetails < ActiveRecord::Migration[8.0]
  def change
    create_table :attack_details do |t|
      t.references :attack_scenario, null: false, foreign_key: true
      t.string :category, null: false
      t.text :description, null: false
      t.integer :severity, null: false, default: 3

      t.timestamps
      t.index [ :attack_scenario_id, :category ], unique: true
    end
  end
end
