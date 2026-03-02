class CreateAttackPromptSets < ActiveRecord::Migration[8.0]
  def change
    create_table :attack_prompt_sets do |t|
      t.references :attack_scenario, foreign_key: true  # 任意：元となったシナリオ
      t.references :attack_prompt_set_generation, foreign_key: true, index: { unique: true }  # 生成イベント
      t.string :name
      t.text :description

      t.timestamps
    end
  end
end
