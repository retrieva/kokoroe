class AiModelConfig
  attr_reader :name, :file_path

  def initialize(name:, file_path:)
    @name = name
    @file_path = file_path
  end

  # NOTE: 攻撃・評価用LLM
  # TODO: 本番環境と開発環境で異なる設定を読み込むようにする
  EVALUATION_LLM = new(
    name: ENV.fetch("EVALUATOR_LLM_NAME", ""),
    file_path: ENV.fetch("EVALUATOR_LLM_PATH", "")
  ).freeze

  # NOTE: 攻撃対象LLM
  TARGET_LLM_PRODUCTION = new(
    name: ENV.fetch("TARGET_LLM", ""),
    file_path: ENV.fetch("TARGET_LLM_PATH_PRODUCTION", "")
  ).freeze
  TARGET_LLM_DEVELOPMENT = new(
    name: ENV.fetch("TARGET_LLM", ""),
    file_path: ENV.fetch("TARGET_LLM_PATH_DEVELOPMENT", "")
  ).freeze
end
