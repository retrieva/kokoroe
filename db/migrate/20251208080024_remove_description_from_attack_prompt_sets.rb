class RemoveDescriptionFromAttackPromptSets < ActiveRecord::Migration[8.0]
  def change
    remove_column :attack_prompt_sets, :description, :text
  end
end
