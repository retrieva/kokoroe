class CreateDefensePolicies < ActiveRecord::Migration[8.0]
  def change
    create_table :defense_policies do |t|
      t.json :contents, null: false, default: []

      t.timestamps
    end
  end
end
