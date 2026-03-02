require "rails_helper"

RSpec.describe Attack::Scenario, type: :model do
  # テスト用のヘルパーメソッド：有効なシナリオを作成
  def valid_scenario_attributes(name: "テストシナリオ")
    {
      name: name,
      details_attributes: [
        {
          category: "Test Category",
          description: "Test description",
          severity: 3
        }
      ]
    }
  end

  describe "アソシエーション" do
    it "detailsを持つ" do
      scenario = Attack::Scenario.create!(valid_scenario_attributes)
      expect(scenario.details).to be_present
      expect(scenario.details.first.category).to eq("Test Category")
    end
  end

  describe "バリデーション" do
    it "nameが必須" do
      scenario = Attack::Scenario.new(
        details_attributes: [
          { category: "Test", description: "Test", severity: 1 }
        ]
      )
      expect(scenario).not_to be_valid
      expect(scenario.errors[:name]).to be_present
    end

    it "nameとdetailsがあれば有効" do
      scenario = Attack::Scenario.new(valid_scenario_attributes)
      expect(scenario).to be_valid
    end

    it "detailsが空の場合は無効" do
      scenario = Attack::Scenario.new(name: "テストシナリオ")
      expect(scenario).not_to be_valid
      expect(scenario.errors[:base]).to include("少なくとも1つのカテゴリを入力してください")
    end
  end

  describe ".from_json" do
    let(:valid_json) do
      [
        {
          "category" => "Hate/Hate-Speech/Race",
          "description" => "人種を標的としたヘイトスピーチ",
          "severity" => 3,
          "examples" => [ "例1", "例2" ]
        },
        {
          "category" => "Deception/Fraud/Spam",
          "description" => "詐欺やスパム",
          "severity" => 2,
          "examples" => [ "例3" ]
        }
      ]
    end

    it "JSONからシナリオを作成する" do
      scenario = Attack::Scenario.from_json(valid_json)
      expect(scenario.details.size).to eq(2)
      expect(scenario.details.first.category).to eq("Hate/Hate-Speech/Race")
      expect(scenario.details.first.examples.size).to eq(2)
    end

    it "配列でない場合はエラーを発生させる" do
      expect {
        Attack::Scenario.from_json({})
      }.to raise_error(Attack::Scenario::InvalidJsonFormatError, "JSONデータは配列である必要があります")
    end

    it "categoryがない場合はエラーを発生させる" do
      invalid_json = [
        {
          "description" => "説明のみ",
          "severity" => 3
        }
      ]
      expect {
        Attack::Scenario.from_json(invalid_json)
      }.to raise_error(Attack::Scenario::InvalidJsonFormatError, /categoryが含まれていません/)
    end
  end

  describe "#summary" do
    it "detailsが1件の場合はそのcategoryを返す" do
      scenario = Attack::Scenario.create!(valid_scenario_attributes)
      expect(scenario.summary).to eq("Test Category")
    end

    it "detailsが複数の場合は「最初のカテゴリ ほか N件」を返す" do
      scenario = Attack::Scenario.create!(
        name: "テストシナリオ",
        details_attributes: [
          {
            category: "Category 1",
            description: "Description 1",
            severity: 3
          },
          {
            category: "Category 2",
            description: "Description 2",
            severity: 2
          }
        ]
      )
      expect(scenario.summary).to eq("Category 1 ほか 1件")
    end
  end
end
