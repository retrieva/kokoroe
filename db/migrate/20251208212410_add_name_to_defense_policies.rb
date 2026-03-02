class AddNameToDefensePolicies < ActiveRecord::Migration[8.0]
  def change
    add_column :defense_policies, :name, :string
  end
end
