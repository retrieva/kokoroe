class CreateAttackPromptSetGenerations < ActiveRecord::Migration[8.0]
  def change
    create_table :attack_prompt_set_generations do |t|
      t.references :attack_scenario, null: false, foreign_key: true
      t.integer :status, default: 0, null: false
      t.json :request_body      # シナリオのスナップショット
      t.json :response_body     # 外部サービスからの生レスポンス
      t.text :error_detail
      t.datetime :started_at
      t.datetime :completed_at
      t.datetime :failed_at

      t.timestamps
    end

    add_index :attack_prompt_set_generations, :status
  end
end
