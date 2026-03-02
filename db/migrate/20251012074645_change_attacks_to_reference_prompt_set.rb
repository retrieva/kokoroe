class ChangeAttacksToReferencePromptSet < ActiveRecord::Migration[8.0]
  def change
    # シナリオへの参照を削除
    remove_foreign_key :attacks, :attack_scenarios
    remove_column :attacks, :attack_scenario_id, :bigint

    # プロンプト集への参照を追加
    add_reference :attacks, :attack_prompt_set, null: false, foreign_key: { to_table: :attack_prompt_sets }
  end
end
