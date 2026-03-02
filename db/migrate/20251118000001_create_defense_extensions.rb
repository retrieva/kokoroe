class CreateDefenseExtensions < ActiveRecord::Migration[8.0]
  def change
    create_table :defense_extensions do |t|
      t.integer :source_policy_id, null: false       # 拡張元防衛方針
      t.integer :extended_policy_id                  # 拡張された防衛方針（拡張処理完了後に設定）
      t.integer :attack_execution_id, null: false    # 参照する攻撃レポート
      t.integer :status, default: 0, null: false     # enum: pending, running, completed, failed
      t.json :request_body                           # AI APIへのリクエスト
      t.json :response_body                          # AI APIからのレスポンス
      t.text :error_detail                           # エラー詳細
      t.datetime :started_at
      t.datetime :completed_at
      t.datetime :failed_at

      t.timestamps
    end

    add_index :defense_extensions, :source_policy_id
    add_index :defense_extensions, :extended_policy_id
    add_index :defense_extensions, :attack_execution_id
    add_index :defense_extensions, :status
    add_foreign_key :defense_extensions, :defense_policies, column: :source_policy_id
    add_foreign_key :defense_extensions, :defense_policies, column: :extended_policy_id
    add_foreign_key :defense_extensions, :attack_executions
  end
end
