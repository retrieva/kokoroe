require 'rails_helper'

RSpec.describe Defense::TrainingDataset, type: :model do
  before do
    # DefenseTrainingDatasetJobが未実装のため、コールバックをスキップ
    Defense::TrainingDataset.skip_callback(:commit, :after, :enqueue_generation_job)
  end

  after do
    # コールバックを復元
    Defense::TrainingDataset.set_callback(:commit, :after, :enqueue_generation_job)
  end

  let(:policy) { create_valid_initial_policy }
  let(:attack_execution) { create_valid_execution }

  describe "アソシエーション" do
    it "policyに属する" do
      dataset = policy.training_datasets.create!(attack_execution: attack_execution)
      expect(dataset.policy).to eq(policy)
    end

    it "attack_executionに属する" do
      dataset = policy.training_datasets.create!(attack_execution: attack_execution)
      expect(dataset.attack_execution).to eq(attack_execution)
    end

    it "attack_executionは必須" do
      dataset = Defense::TrainingDataset.new(policy: policy)
      expect(dataset).not_to be_valid
      expect(dataset.errors[:attack_execution]).to be_present
    end
  end

  describe "バリデーション" do
    it "statusはデフォルトでpending" do
      dataset = Defense::TrainingDataset.new(policy: policy, attack_execution: attack_execution)
      expect(dataset).to be_valid
      expect(dataset.status).to eq("pending")
    end
  end

  describe "ステータス管理" do
    let(:dataset) { policy.training_datasets.create!(attack_execution: attack_execution) }

    describe "#start!" do
      it "pendingからrunningに変更できる" do
        dataset.send(:start!)
        expect(dataset.status).to eq("running")
        expect(dataset.started_at).to be_present
      end

      it "pending以外からは実行できない" do
        dataset.update!(status: :running, started_at: Time.current)
        expect {
          dataset.send(:start!)
        }.to raise_error(StandardError, /Cannot start with status/)
      end
    end

    describe "#complete!" do
      it "runningからcompletedに変更できる" do
        dataset.update!(status: :running, started_at: Time.current)
        dataset.send(:complete!)
        expect(dataset.status).to eq("completed")
        expect(dataset.completed_at).to be_present
      end

      it "running以外からは実行できない" do
        dataset.update!(status: :pending)
        expect {
          dataset.send(:complete!)
        }.to raise_error(StandardError, /Cannot complete with status/)
      end
    end
  end

  describe "スコープ" do
    it "recentスコープで作成日時の降順で取得できる" do
      dataset1 = policy.training_datasets.create!(attack_execution: attack_execution, created_at: 3.days.ago)
      dataset2 = policy.training_datasets.create!(attack_execution: attack_execution, created_at: 1.day.ago)
      dataset3 = policy.training_datasets.create!(attack_execution: attack_execution, created_at: 2.days.ago)

      dataset_ids = [ dataset1.id, dataset2.id, dataset3.id ]
      recent_datasets = Defense::TrainingDataset.where(id: dataset_ids).recent
      expect(recent_datasets.to_a).to eq([ dataset2, dataset3, dataset1 ])
    end
  end
end
