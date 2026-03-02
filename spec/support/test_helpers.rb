module TestHelpers
  # 有効なシナリオの属性を返す
  def valid_scenario_attributes(name: "テストシナリオ")
    {
      name: name,
      details_attributes: [
        {
          category: "Test Category",
          description: "Test description",
          severity: 3,
          examples_attributes: [
            { text: "テスト例" }
          ]
        }
      ]
    }
  end

  # 有効なシナリオを作成
  def create_valid_scenario(name: "テストシナリオ")
    Attack::Scenario.create!(valid_scenario_attributes(name: name))
  end

  # 有効なプロンプト集を作成
  def create_valid_prompt_set(scenario: nil, name: "テストプロンプト集", status: :completed)
    scenario ||= create_valid_scenario
    attrs = {
      name: name,
      scenario: scenario,
      status: status
    }
    attrs[:completed_at] = Time.current if status == :completed
    attrs[:failed_at] = Time.current if status == :failed
    Attack::PromptSet.create!(attrs)
  end

  # 有効な攻撃実行を作成
  def create_valid_execution(prompt_set: nil, status: :completed)
    prompt_set ||= create_valid_prompt_set
    attrs = {
      prompt_set: prompt_set,
      name: "テスト攻撃",
      status: status
    }
    attrs[:completed_at] = Time.current if status == :completed
    attrs[:failed_at] = Time.current if status == :failed
    Attack::Execution.create!(attrs)
  end

  # 有効な初期防衛方針を作成
  def create_valid_initial_policy(name: "テスト初期方針")
    Defense::Policy.create!(
      name: name,
      contents: [ "テスト防衛方針" ],
      status: :completed
    )
  end

  # 有効な拡張防衛方針を作成
  def create_valid_extended_policy(source_policy: nil, attack_execution: nil, name: "テスト拡張方針")
    source_policy ||= create_valid_initial_policy
    attack_execution ||= create_valid_execution
    Defense::Policy.create!(
      name: name,
      contents: [ "テスト防衛方針" ],
      source_policy: source_policy,
      attack_execution: attack_execution,
      status: :completed
    )
  end

  # 有効な学習データセットを作成
  def create_valid_training_dataset(policy: nil, attack_execution: nil, status: :completed)
    policy ||= create_valid_extended_policy
    attack_execution ||= policy.attack_execution
    attrs = {
      policy: policy,
      attack_execution: attack_execution,
      status: status
    }
    attrs[:completed_at] = Time.current if status == :completed
    attrs[:failed_at] = Time.current if status == :failed
    Defense::TrainingDataset.create!(attrs)
  end
end

RSpec.configure do |config|
  config.include TestHelpers
end
