require "rails_helper"

RSpec.describe Attack::PromptSet, type: :model do
  let(:scenario) { create_valid_scenario }

  describe "アソシエーション" do
    it "scenarioに属する" do
      prompt_set = Attack::PromptSet.create!(
        scenario: scenario,
        name: "テストプロンプト集",
        status: :completed,
        completed_at: Time.current
      )
      expect(prompt_set.scenario).to eq(scenario)
    end

    it "promptsを持つ" do
      prompt_set = Attack::PromptSet.create!(
        scenario: scenario,
        name: "テストプロンプト集",
        status: :completed,
        completed_at: Time.current
      )
      prompt = prompt_set.prompts.create!(
        category: "Test Category",
        text: "テストプロンプト"
      )
      expect(prompt_set.prompts).to include(prompt)
    end

    it "executionsを持つ" do
      prompt_set = Attack::PromptSet.create!(
        scenario: scenario,
        name: "テストプロンプト集",
        status: :completed,
        completed_at: Time.current
      )
      execution = prompt_set.executions.create!(name: "テスト攻撃", status: :completed, completed_at: Time.current)
      expect(prompt_set.executions).to include(execution)
    end
  end

  describe "バリデーション" do
    it "nameが必須" do
      prompt_set = Attack::PromptSet.new(scenario: scenario)
      expect(prompt_set).not_to be_valid
      expect(prompt_set.errors[:name]).to be_present
    end

    it "nameがあれば有効" do
      prompt_set = Attack::PromptSet.new(
        scenario: scenario,
        name: "テストプロンプト集"
      )
      expect(prompt_set).to be_valid
    end
  end

  describe "#build_prompts" do
    let(:prompt_set) do
      Attack::PromptSet.create!(
        scenario: scenario,
        name: "テストプロンプト集",
        status: :completed,
        completed_at: Time.current
      )
    end

    it "レスポンスからプロンプトを作成する" do
      response = {
        prompts: [
          { category: "Category A", text: "Prompt 1" },
          { category: "Category B", text: "Prompt 2" },
          { category: "Category A", text: "Prompt 3" }
        ]
      }

      prompt_set.build_prompts(response)
      prompt_set.save!

      expect(prompt_set.prompts.count).to eq(3)
      expect(prompt_set.prompts.first.category).to eq("Category A")
      expect(prompt_set.prompts.first.text).to eq("Prompt 1")
      expect(prompt_set.prompts.first.position).to eq(1)
    end

    it "文字列キーでも動作する" do
      response = {
        "prompts" => [
          { "category" => "Category A", "text" => "Prompt 1" }
        ]
      }

      prompt_set.build_prompts(response)
      prompt_set.save!

      expect(prompt_set.prompts.count).to eq(1)
    end

    it "ハッシュでない場合は何もしない" do
      prompt_set.build_prompts("not a hash")
      expect(prompt_set.prompts.count).to eq(0)
    end
  end

  describe "#categorized_prompts" do
    let(:prompt_set) do
      Attack::PromptSet.create!(
        scenario: scenario,
        name: "テストプロンプト集",
        status: :completed,
        completed_at: Time.current
      )
    end

    before do
      prompt_set.prompts.create!(
        category: "Category A",
        text: "Prompt 1",
        position: 1
      )
      prompt_set.prompts.create!(
        category: "Category B",
        text: "Prompt 2",
        position: 2
      )
      prompt_set.prompts.create!(
        category: "Category A",
        text: "Prompt 3",
        position: 3
      )
    end

    it "カテゴリごとにグループ化されたプロンプトを返す" do
      categorized = prompt_set.categorized_prompts

      expect(categorized.keys).to contain_exactly("Category A", "Category B")
      expect(categorized["Category A"].count).to eq(2)
      expect(categorized["Category B"].count).to eq(1)
    end

    it "position順に並んでいる" do
      categorized = prompt_set.categorized_prompts

      expect(categorized["Category A"].pluck(:text)).to eq([ "Prompt 1", "Prompt 3" ])
    end
  end
end
