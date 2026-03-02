require "rails_helper"

RSpec.describe Attack::Example, type: :model do
  let(:scenario) { create_valid_scenario }
  let(:detail) { scenario.details.first }

  describe "アソシエーション" do
    it "detailに属する" do
      example = detail.examples.create!(text: "例1")
      expect(example.detail).to eq(detail)
    end
  end

  describe "バリデーション" do
    it "textが必須" do
      example = Attack::Example.new(detail: detail)
      expect(example).not_to be_valid
      expect(example.errors[:text]).to be_present
    end

    it "textがあれば有効" do
      example = Attack::Example.new(detail: detail, text: "例1")
      expect(example).to be_valid
    end
  end

  describe "#empty?" do
    it "textが空の場合はtrue" do
      example = detail.examples.build
      expect(example.empty?).to be true
    end

    it "textがある場合はfalse" do
      example = detail.examples.build(text: "例1")
      expect(example.empty?).to be false
    end
  end

  describe "#as_json" do
    it "テキストそのものを返す" do
      example = detail.examples.create!(text: "例1")
      expect(example.as_json).to eq("例1")
    end
  end
end
