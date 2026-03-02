require 'rails_helper'

RSpec.describe Defense::Policy, type: :model do
  describe "アソシエーション" do
    let(:initial_policy) { create_valid_initial_policy }
    let(:attack_execution) { create_valid_execution }

    it "extended_policiesを持つ" do
      extended_policy = Defense::Policy.create!(
        name: "拡張方針",
        source_policy: initial_policy,
        attack_execution: attack_execution,
        contents: [ "拡張された方針" ],
        status: :completed
      )
      expect(initial_policy.extended_policies).to include(extended_policy)
    end

    it "source_policyに属する（拡張方針の場合）" do
      extended_policy = Defense::Policy.create!(
        name: "拡張方針",
        source_policy: initial_policy,
        attack_execution: attack_execution,
        contents: [ "拡張された方針" ],
        status: :completed
      )
      expect(extended_policy.source_policy).to eq(initial_policy)
    end

    it "拡張方針がある場合は削除できない" do
      Defense::Policy.create!(
        name: "拡張方針",
        source_policy: initial_policy,
        attack_execution: attack_execution,
        contents: [ "拡張された方針" ],
        status: :completed
      )

      expect(initial_policy.destroy).to be false
      expect(initial_policy.errors[:base]).to be_present
    end
  end

  describe "バリデーション" do
    it "nameが必須" do
      policy = Defense::Policy.new(name: nil, contents: [ "方針" ])
      expect(policy).not_to be_valid
      expect(policy.errors[:name]).to be_present
    end

    it "contentsは完了時に必須" do
      policy = Defense::Policy.new(name: "テスト", contents: nil, status: :completed)
      expect(policy).not_to be_valid
      expect(policy.errors[:contents]).to be_present
    end

    it "contentsが空配列の場合、完了時は無効" do
      policy = Defense::Policy.new(name: "テスト", contents: [], status: :completed)
      expect(policy).not_to be_valid
    end

    it "contentsが配列でない場合、完了時は無効" do
      policy = Defense::Policy.new(name: "テスト", contents: "文字列", status: :completed)
      expect(policy).not_to be_valid
      expect(policy.errors[:contents]).to include("must be an array")
    end

    it "nameとcontentsが配列の場合は有効" do
      policy = Defense::Policy.new(name: "テスト", contents: [ "方針1", "方針2" ], status: :completed)
      expect(policy).to be_valid
    end

    it "pendingの場合はcontentsは不要" do
      policy = Defense::Policy.new(name: "テスト", contents: nil, status: :pending)
      expect(policy).to be_valid
    end
  end

  describe "スコープ" do
    it "recentスコープで作成日時の降順で取得できる" do
      policy1 = Defense::Policy.create!(
        name: "方針1",
        contents: [ "方針1" ],
        status: :completed,
        created_at: 3.days.ago
      )
      policy2 = Defense::Policy.create!(
        name: "方針2",
        contents: [ "方針2" ],
        status: :completed,
        created_at: 1.day.ago
      )
      policy3 = Defense::Policy.create!(
        name: "方針3",
        contents: [ "方針3" ],
        status: :completed,
        created_at: 2.days.ago
      )

      policy_ids = [ policy1.id, policy2.id, policy3.id ]
      recent_policies = Defense::Policy.where(id: policy_ids).recent
      expect(recent_policies.to_a).to eq([ policy2, policy3, policy1 ])
    end

    it "initialスコープで初期方針のみ取得できる" do
      initial_policy = create_valid_initial_policy
      attack_execution = create_valid_execution
      extended_policy = Defense::Policy.create!(
        name: "拡張方針",
        source_policy: initial_policy,
        attack_execution: attack_execution,
        contents: [ "拡張された方針" ],
        status: :completed
      )

      expect(Defense::Policy.initial).to include(initial_policy)
      expect(Defense::Policy.initial).not_to include(extended_policy)
    end

    it "extendedスコープで拡張方針のみ取得できる" do
      initial_policy = create_valid_initial_policy
      attack_execution = create_valid_execution
      extended_policy = Defense::Policy.create!(
        name: "拡張方針",
        source_policy: initial_policy,
        attack_execution: attack_execution,
        contents: [ "拡張された方針" ],
        status: :completed
      )

      expect(Defense::Policy.extended).to include(extended_policy)
      expect(Defense::Policy.extended).not_to include(initial_policy)
    end
  end
end
