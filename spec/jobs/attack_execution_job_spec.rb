require 'rails_helper'

RSpec.describe AttackExecutionJob, type: :job do
  let(:scenario) { create_valid_scenario }
  let(:prompt_set) do
    Attack::PromptSet.create!(
      scenario: scenario,
      name: "test_prompt_set",
      status: :completed,
      completed_at: Time.current
    ).tap do |ps|
      ps.prompts.create!(category: "Test", text: "Test prompt", position: 1)
    end
  end

  before do
    allow(ENV).to receive(:[]).and_call_original
    allow(ENV).to receive(:[]).with('USE_DUMMY_ATTACK').and_return('true')
    Attack::ExecutionClient.force_next_failure = false

    # コールバックをスキップ（このテストではジョブを手動で実行するため）
    Attack::Execution.skip_callback(:commit, :after, :enqueue_execution_job)
  end

  after do
    # コールバックを復元
    Attack::Execution.set_callback(:commit, :after, :enqueue_execution_job)
  end

  let(:execution) { Attack::Execution.create!(prompt_set: prompt_set, name: "テスト攻撃") }

  describe "#perform" do
    context "攻撃が成功する場合" do
      it "攻撃を実行し、完了状態にする" do
        described_class.new.perform(execution.id)

        execution.reload
        expect(execution.completed?).to be true
        expect(execution.response_body).to be_present
        expect(execution.started_at).to be_present
        expect(execution.completed_at).to be_present
      end
    end

    context "攻撃が失敗する場合" do
      it "攻撃を失敗状態にして例外を再送出する" do
        # 次のリクエストを失敗させる
        Attack::ExecutionClient.force_next_failure = true

        expect {
          described_class.new.perform(execution.id)
        }.to raise_error(StandardError, "Forced failure for testing")

        execution.reload
        expect(execution.failed?).to be true
        expect(execution.started_at).to be_present
        expect(execution.failed_at).to be_present
      end
    end
  end
end
