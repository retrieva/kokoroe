require "rails_helper"

RSpec.describe Attack::Detail, type: :model do
  let(:scenario) { create_valid_scenario }

  describe "アソシエーション" do
    it "scenarioに属する" do
      detail = scenario.details.first
      expect(detail.scenario).to eq(scenario)
    end

    it "examplesを持つ" do
      detail = scenario.details.first
      example = detail.examples.create!(text: "例1")
      expect(detail.examples).to include(example)
    end
  end

  describe "バリデーション" do
    it "categoryが必須" do
      detail = Attack::Detail.new(
        scenario: scenario,
        description: "Test description",
        severity: 3
      )
      expect(detail).not_to be_valid
      expect(detail.errors[:category]).to be_present
    end

    it "descriptionが必須" do
      detail = Attack::Detail.new(
        scenario: scenario,
        category: "Test Category",
        severity: 3
      )
      expect(detail).not_to be_valid
      expect(detail.errors[:description]).to be_present
    end

    it "severityは1から5の範囲" do
      # severityにnilをセットするとデフォルトで3になる
      detail = scenario.details.build(
        category: "Other Category",  # 一意になるようにカテゴリを変更
        description: "Test description",
        severity: nil
      )
      detail.valid?
      expect(detail.severity).to eq(3)  # デフォルト値が設定される

      # 範囲外の値は無効
      detail.severity = 6
      expect(detail).not_to be_valid

      # 範囲内の値は有効
      detail.severity = 3
      expect(detail).to be_valid
    end
  end

  describe "#empty?" do
    it "category、description、examplesが全て空の場合はtrue" do
      detail = scenario.details.build
      expect(detail.empty?).to be true
    end

    it "categoryがある場合はfalse" do
      detail = scenario.details.build(category: "Test")
      expect(detail.empty?).to be false
    end

    it "descriptionがある場合はfalse" do
      detail = scenario.details.build(description: "Test")
      expect(detail.empty?).to be false
    end
  end
end
