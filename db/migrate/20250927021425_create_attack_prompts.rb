class CreateAttackPrompts < ActiveRecord::Migration[8.0]
  def change
    create_table :attack_prompts do |t|
      t.references :attack_prompt_set, null: false, foreign_key: true
      t.string :category, null: false
      t.text :text, null: false
      t.json :raw_data
      t.integer :position

      t.timestamps
    end

    add_index :attack_prompts, :category
    add_index :attack_prompts, :position
  end
end
