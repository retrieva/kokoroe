class MergePromptSetGenerationsIntoPromptSets < ActiveRecord::Migration[8.0]
  def change
    # attack_prompt_setsにカラムを追加
    add_column :attack_prompt_sets, :status, :integer, default: 0, null: false
    add_column :attack_prompt_sets, :request_body, :json
    add_column :attack_prompt_sets, :response_body, :json
    add_column :attack_prompt_sets, :error_detail, :text
    add_column :attack_prompt_sets, :started_at, :datetime
    add_column :attack_prompt_sets, :completed_at, :datetime
    add_column :attack_prompt_sets, :failed_at, :datetime
    add_index :attack_prompt_sets, :status

    # 外部キー参照を削除
    remove_reference :attack_prompt_sets, :attack_prompt_set_generation, foreign_key: true, index: { unique: true }

    # attack_prompt_set_generationsテーブルを削除
    drop_table :attack_prompt_set_generations do |t|
      t.references :attack_scenario, null: false, foreign_key: true
      t.integer :status, default: 0, null: false
      t.json :request_body
      t.json :response_body
      t.text :error_detail
      t.datetime :started_at
      t.datetime :completed_at
      t.datetime :failed_at
      t.timestamps

      t.index :status
    end
  end
end
