class CreateAttackExamples < ActiveRecord::Migration[8.0]
  def change
    create_table :attack_examples do |t|
      t.references :attack_detail, null: false, foreign_key: true
      t.text :text, null: false

      t.timestamps
      t.index [ :attack_detail_id, :text ], unique: true
    end
  end
end
