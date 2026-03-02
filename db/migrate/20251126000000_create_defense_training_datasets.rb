class CreateDefenseTrainingDatasets < ActiveRecord::Migration[8.0]
  def change
    create_table :defense_training_datasets do |t|
      t.integer :defense_policy_id, null: false        # 使用する防衛方針
      t.integer :attack_execution_id                   # 参照する攻撃実行結果（オプション）
      t.integer :status, default: 0, null: false       # enum: pending, running, completed, failed

      # 生成されたファイルのパス
      t.string :red_prompt_path                        # ステップ1: 攻撃プロンプト
      t.string :response_path                          # ステップ2: 応答
      t.string :corrected_response_path                # ステップ3: 修正後の応答
      t.string :sft_data_path                          # ステップ4: SFT用学習データ
      t.string :dpo_data_path                          # ステップ4: DPO用学習データ
      t.string :report_path                            # ステップ4: レポート

      # レポート内容（JSON）
      t.json :report_body

      # エラー情報
      t.text :error_detail

      # タイムスタンプ
      t.datetime :started_at
      t.datetime :completed_at
      t.datetime :failed_at
      t.timestamps
    end

    add_index :defense_training_datasets, :defense_policy_id
    add_index :defense_training_datasets, :attack_execution_id
    add_index :defense_training_datasets, :status
    add_foreign_key :defense_training_datasets, :defense_policies
    add_foreign_key :defense_training_datasets, :attack_executions
  end
end
