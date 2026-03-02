class MergeExtensionsIntoPolicies < ActiveRecord::Migration[8.0]
  def change
    # defense_policiesにカラムを追加
    add_reference :defense_policies, :source_policy, foreign_key: { to_table: :defense_policies }, index: true
    add_reference :defense_policies, :attack_execution, foreign_key: true, index: true
    add_column :defense_policies, :status, :integer, default: 0, null: false
    add_column :defense_policies, :request_body, :json
    add_column :defense_policies, :response_body, :json
    add_column :defense_policies, :error_detail, :text
    add_column :defense_policies, :started_at, :datetime
    add_column :defense_policies, :completed_at, :datetime
    add_column :defense_policies, :failed_at, :datetime
    add_index :defense_policies, :status

    # defense_extensionsテーブルを削除
    drop_table :defense_extensions do |t|
      t.references :source_policy, null: false, foreign_key: { to_table: :defense_policies }
      t.references :extended_policy, foreign_key: { to_table: :defense_policies }
      t.references :attack_execution, null: false, foreign_key: true
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
