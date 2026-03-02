require "rails_helper"

RSpec.describe Attack::Prompt, type: :model do
  let(:scenario) { create_valid_scenario }
  let(:prompt_set) do
    Attack::PromptSet.create!(
      scenario: scenario,
      name: "テストプロンプト集",
      status: :completed,
      completed_at: Time.current
    )
  end

  describe "アソシエーション" do
    it "prompt_setに属する" do
      prompt = prompt_set.prompts.create!(
        category: "Test Category",
        text: "テストプロンプト"
      )
      expect(prompt.prompt_set).to eq(prompt_set)
    end
  end

  describe "バリデーション" do
    it "categoryが必須" do
      prompt = Attack::Prompt.new(
        prompt_set: prompt_set,
        text: "テストプロンプト"
      )
      expect(prompt).not_to be_valid
      expect(prompt.errors[:category]).to be_present
    end

    it "textが必須" do
      prompt = Attack::Prompt.new(
        prompt_set: prompt_set,
        category: "Test Category"
      )
      expect(prompt).not_to be_valid
      expect(prompt.errors[:text]).to be_present
    end

    it "categoryとtextがあれば有効" do
      prompt = Attack::Prompt.new(
        prompt_set: prompt_set,
        category: "Test Category",
        text: "テストプロンプト"
      )
      expect(prompt).to be_valid
    end
  end

  describe "スコープ" do
    before do
      prompt_set.prompts.create!(
        category: "Category A",
        text: "Prompt 1",
        position: 2
      )
      prompt_set.prompts.create!(
        category: "Category B",
        text: "Prompt 2",
        position: 1
      )
      prompt_set.prompts.create!(
        category: "Category A",
        text: "Prompt 3",
        position: 3
      )
    end

    describe ".in_category" do
      it "指定されたカテゴリのプロンプトを返す" do
        prompts = Attack::Prompt.in_category("Category A")
        expect(prompts.count).to eq(2)
        expect(prompts.pluck(:text)).to contain_exactly("Prompt 1", "Prompt 3")
      end
    end

    describe ".ordered" do
      it "position順に並べて返す" do
        prompts = prompt_set.prompts.ordered
        expect(prompts.pluck(:text)).to eq([ "Prompt 2", "Prompt 1", "Prompt 3" ])
      end
    end
  end
end
