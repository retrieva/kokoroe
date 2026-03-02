require "rails_helper"

RSpec.describe Attack::Execution, type: :model do
  let(:scenario) { create_valid_scenario }
  let(:prompt_set) do
    Attack::PromptSet.create!(
      scenario: scenario,
      name: "テストプロンプト集",
      status: :completed,
      completed_at: Time.current
    )
  end
  let(:execution) do
    Attack::Execution.create!(
      prompt_set: prompt_set,
      name: "テスト攻撃",
      status: :completed,
      completed_at: Time.current
    )
  end

  describe "アソシエーション" do
    it "Attack::PromptSetに属する" do
      expect(execution.prompt_set).to eq(prompt_set)
    end

    it "defense_policiesを持つ" do
      source_policy = create_valid_initial_policy
      extended_policy = Defense::Policy.create!(
        name: "拡張方針",
        source_policy: source_policy,
        attack_execution: execution,
        contents: [ "拡張方針" ],
        status: :completed
      )
      expect(execution.defense_policies).to include(extended_policy)
    end
  end

  describe "enumの定義" do
    it "statusがenumとして定義されている" do
      expect(Attack::Execution.statuses).to eq({
        "pending" => 0,
        "running" => 1,
        "completed" => 2,
        "failed" => 3
      })
    end

    it "デフォルトのステータスはpending" do
      new_execution = Attack::Execution.new(prompt_set: prompt_set, name: "test")
      expect(new_execution).to be_pending
    end
  end

  describe "#execution_time" do
    context "開始時刻と完了時刻がある場合" do
      it "実行時間を返す" do
        execution.update_columns(
          started_at: Time.parse("2025-01-01 10:00:00"),
          completed_at: Time.parse("2025-01-01 10:05:30")
        )
        expect(execution.execution_time).to eq(330.0)
      end
    end

    context "開始時刻と失敗時刻がある場合" do
      it "実行時間を返す" do
        execution.update_columns(
          status: :failed,
          started_at: Time.parse("2025-01-01 10:00:00"),
          failed_at: Time.parse("2025-01-01 10:02:15"),
          completed_at: nil
        )
        expect(execution.execution_time).to eq(135.0)
      end
    end

    context "開始時刻がない場合" do
      it "nilを返す" do
        execution.update_columns(started_at: nil)
        expect(execution.execution_time).to be_nil
      end
    end
  end

  describe "#start!" do
    let(:pending_execution) do
      exec = Attack::Execution.create!(
        prompt_set: prompt_set,
        name: "テスト攻撃",
        status: :completed,
        completed_at: Time.current
      )
      exec.update_columns(status: :pending, completed_at: nil)
      exec.reload
    end

    context "ステータスがpendingの場合" do
      it "ステータスをrunningに変更し、開始時刻を記録する" do
        expect {
          pending_execution.send(:start!)
        }.to change { pending_execution.status }.from("pending").to("running")
          .and change { pending_execution.started_at }.from(nil)
      end
    end

    context "ステータスがpending以外の場合" do
      it "例外を発生させる" do
        pending_execution.update_columns(status: :running)
        expect {
          pending_execution.send(:start!)
        }.to raise_error(StandardError, "Cannot start with status: running")
      end
    end
  end

  describe "#complete!" do
    let(:response_data) { { "response" => { "overall-summary" => "test summary" } } }
    let(:running_execution) do
      exec = Attack::Execution.create!(
        prompt_set: prompt_set,
        name: "テスト攻撃",
        status: :completed,
        completed_at: Time.current
      )
      exec.update_columns(status: :running, started_at: Time.current, completed_at: nil)
      exec.reload
    end

    context "ステータスがrunningの場合" do
      it "ステータスをcompletedに変更し、レスポンスと完了時刻を記録する" do
        expect {
          running_execution.send(:complete!, response_body: response_data)
        }.to change { running_execution.status }.from("running").to("completed")
          .and change { running_execution.response_body }.from(nil).to(response_data)
          .and change { running_execution.completed_at }.from(nil)
      end
    end

    context "ステータスがrunning以外の場合" do
      it "例外を発生させる" do
        pending_execution = Attack::Execution.create!(
          prompt_set: prompt_set,
          name: "テスト攻撃",
          status: :completed,
          completed_at: Time.current
        )
        pending_execution.update_columns(status: :pending, completed_at: nil)
        expect {
          pending_execution.send(:complete!, response_body: response_data)
        }.to raise_error(StandardError, "Cannot complete with status: pending")
      end
    end
  end
end
