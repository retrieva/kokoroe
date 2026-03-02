class CreateAttacks < ActiveRecord::Migration[8.0]
  def change
    create_table :attacks do |t|
      t.references :attack_scenario, null: false, foreign_key: { to_table: :attack_scenarios }
      t.integer :status, default: 0, null: false
      t.json :request_body      # 外部システムに送信するJSON（シナリオのスナップショット）
      t.json :response_body     # 外部システムからの実行結果JSON
      t.text :error_detail      # エラー発生時の詳細情報
      t.datetime :started_at    # 実行開始時刻
      t.datetime :completed_at  # 実行完了時刻
      t.datetime :failed_at     # 実行失敗時刻

      t.timestamps
    end

    add_index :attacks, :status
    add_index :attacks, :started_at
  end
end
