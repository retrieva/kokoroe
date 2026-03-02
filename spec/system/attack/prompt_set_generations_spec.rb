require 'rails_helper'

RSpec.describe "Attack::PromptSetGenerations", type: :system do
  let(:scenario) do
    Attack::Scenario.create!(
      name: "テストシナリオ",
      details_attributes: [
        {
          category: "Hate/Hate-Speech/Race",
          description: "人種を標的としたヘイトスピーチ",
          severity: 3,
          examples_attributes: [
            { text: "例1" }
          ]
        }
      ]
    )
  end

  describe "一覧画面" do
    it "生成履歴が1つ表示される" do
      # プロンプト集を作成（完了状態で）
      prompt_set = Attack::PromptSet.create!(
        name: "テストプロンプト集",
        scenario: scenario,
        status: :completed,
        completed_at: Time.current
      )

      visit attack_prompt_sets_path

      # テーブルにプロンプト集が表示される
      expect(page).to have_content("テストプロンプト集")
      expect(page).to have_content("完了")
    end

    it "シナリオで絞り込みができる" do
      scenario2 = Attack::Scenario.create!(
        name: "テストシナリオ2",
        details_attributes: [
          {
            category: "Test",
            description: "テスト",
            severity: 1,
            examples_attributes: [ { text: "例" } ]
          }
        ]
      )

      prompt_set1 = Attack::PromptSet.create!(
        name: "プロンプト集1",
        scenario: scenario,
        status: :completed,
        completed_at: Time.current
      )
      prompt_set2 = Attack::PromptSet.create!(
        name: "プロンプト集2",
        scenario: scenario2,
        status: :completed,
        completed_at: Time.current
      )

      visit attack_prompt_sets_path

      # 両方表示される
      expect(page).to have_content("プロンプト集1")
      expect(page).to have_content("プロンプト集2")

      # シナリオ1で絞り込み
      select scenario.name, from: "シナリオ"
      click_button "絞り込む"

      # テーブル内にシナリオ1のプロンプト集のみ表示される
      within "table tbody" do
        expect(page).to have_content("プロンプト集1")
        expect(page).not_to have_content("プロンプト集2")
      end
    end

    it "ステータスで絞り込みができる" do
      prompt_set1 = Attack::PromptSet.create!(
        name: "プロンプト集1",
        scenario: scenario,
        status: :completed,
        completed_at: Time.current
      )
      prompt_set2 = Attack::PromptSet.create!(
        name: "プロンプト集2",
        scenario: scenario,
        status: :failed,
        failed_at: Time.current
      )

      visit attack_prompt_sets_path

      # 両方表示される
      expect(page).to have_css(".badge.bg-success", text: "完了")
      expect(page).to have_css(".badge.bg-danger", text: "失敗")

      # 完了で絞り込み
      select "完了", from: "ステータス"
      click_button "絞り込む"

      # 完了のみ表示される
      expect(page).to have_css(".badge.bg-success", text: "完了")
      expect(page).not_to have_css(".badge.bg-danger", text: "失敗")
    end
  end
end
