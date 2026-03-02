# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[8.0].define(version: 2025_12_08_224025) do
  create_table "attack_details", force: :cascade do |t|
    t.integer "attack_scenario_id", null: false
    t.string "category", null: false
    t.text "description", null: false
    t.integer "severity", default: 3, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["attack_scenario_id", "category"], name: "index_attack_details_on_attack_scenario_id_and_category", unique: true
    t.index ["attack_scenario_id"], name: "index_attack_details_on_attack_scenario_id"
  end

  create_table "attack_examples", force: :cascade do |t|
    t.integer "attack_detail_id", null: false
    t.text "text", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["attack_detail_id", "text"], name: "index_attack_examples_on_attack_detail_id_and_text", unique: true
    t.index ["attack_detail_id"], name: "index_attack_examples_on_attack_detail_id"
  end

  create_table "attack_executions", force: :cascade do |t|
    t.integer "status", default: 0, null: false
    t.json "request_body"
    t.json "response_body"
    t.text "error_detail"
    t.datetime "started_at"
    t.datetime "completed_at"
    t.datetime "failed_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.integer "attack_prompt_set_id", null: false
    t.integer "current_step"
    t.datetime "cycle_updated_at"
    t.string "name", default: "", null: false
    t.index ["attack_prompt_set_id"], name: "index_attack_executions_on_attack_prompt_set_id"
    t.index ["started_at"], name: "index_attack_executions_on_started_at"
    t.index ["status"], name: "index_attack_executions_on_status"
  end

  create_table "attack_prompt_sets", force: :cascade do |t|
    t.integer "attack_scenario_id"
    t.string "name"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.datetime "cycle_updated_at"
    t.integer "status", default: 0, null: false
    t.json "request_body"
    t.json "response_body"
    t.text "error_detail"
    t.datetime "started_at"
    t.datetime "completed_at"
    t.datetime "failed_at"
    t.index ["attack_scenario_id"], name: "index_attack_prompt_sets_on_attack_scenario_id"
    t.index ["status"], name: "index_attack_prompt_sets_on_status"
  end

  create_table "attack_prompts", force: :cascade do |t|
    t.integer "attack_prompt_set_id", null: false
    t.string "category", null: false
    t.text "text", null: false
    t.json "raw_data"
    t.integer "position"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["attack_prompt_set_id"], name: "index_attack_prompts_on_attack_prompt_set_id"
    t.index ["category"], name: "index_attack_prompts_on_category"
    t.index ["position"], name: "index_attack_prompts_on_position"
  end

  create_table "attack_scenarios", force: :cascade do |t|
    t.string "name", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.datetime "cycle_updated_at"
  end

  create_table "defense_policies", force: :cascade do |t|
    t.json "contents", default: [], null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.datetime "cycle_updated_at"
    t.integer "source_policy_id"
    t.integer "attack_execution_id"
    t.integer "status", default: 0, null: false
    t.json "request_body"
    t.json "response_body"
    t.text "error_detail"
    t.datetime "started_at"
    t.datetime "completed_at"
    t.datetime "failed_at"
    t.string "name"
    t.index ["attack_execution_id"], name: "index_defense_policies_on_attack_execution_id"
    t.index ["source_policy_id"], name: "index_defense_policies_on_source_policy_id"
    t.index ["status"], name: "index_defense_policies_on_status"
  end

  create_table "defense_training_datasets", force: :cascade do |t|
    t.integer "defense_policy_id", null: false
    t.integer "attack_execution_id"
    t.integer "status", default: 0, null: false
    t.string "red_prompt_path"
    t.string "response_path"
    t.string "corrected_response_path"
    t.string "sft_data_path"
    t.string "dpo_data_path"
    t.string "report_path"
    t.json "report_body"
    t.text "error_detail"
    t.datetime "started_at"
    t.datetime "completed_at"
    t.datetime "failed_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.integer "current_step", default: 0
    t.datetime "cycle_updated_at"
    t.string "name"
    t.index ["attack_execution_id"], name: "index_defense_training_datasets_on_attack_execution_id"
    t.index ["defense_policy_id"], name: "index_defense_training_datasets_on_defense_policy_id"
    t.index ["status"], name: "index_defense_training_datasets_on_status"
  end

  add_foreign_key "attack_details", "attack_scenarios"
  add_foreign_key "attack_examples", "attack_details"
  add_foreign_key "attack_executions", "attack_prompt_sets"
  add_foreign_key "attack_prompt_sets", "attack_scenarios"
  add_foreign_key "attack_prompts", "attack_prompt_sets"
  add_foreign_key "defense_policies", "attack_executions"
  add_foreign_key "defense_policies", "defense_policies", column: "source_policy_id"
  add_foreign_key "defense_training_datasets", "attack_executions"
  add_foreign_key "defense_training_datasets", "defense_policies"
end
