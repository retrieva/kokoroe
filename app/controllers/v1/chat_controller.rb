# 開発用のダミーのOpenAI API互換のレスポンスを返すコントローラー
class V1::ChatController < ApplicationController
  # API エンドポイントのためCSRF保護を無効化
  skip_before_action :verify_authenticity_token

  def completions
    # OpenAI API互換のレスポンス形式
    response_data = {
      id: "chatcmpl-#{SecureRandom.hex(10)}",
      object: "chat.completion",
      created: Time.current.to_i,
      model: params[:model],
      choices: [
        {
          index: 0,
          message: {
            role: "assistant",
            content: generate_response(params[:messages])
          },
          finish_reason: "stop"
        }
      ],
      usage: {
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0
      }
    }

    render json: response_data
  end

  private

  def generate_response(messages)
    # リクエストの内容を確認して適切なレスポンスを生成
    message_content = messages&.first&.dig("content") || ""

    if message_content.include?("question") || message_content.include?("質問")
      # 質問生成のリクエストの場合（GeneratedPromptFormat）
      {
        "question": "これはダミーの攻撃的な質問です。"
      }.to_json
    elsif message_content.include?("scenarios")
      # シナリオ生成のリクエストの場合（DetailAttackScenarioFormat）
      {
        "scenarios": [
          "ダミー攻撃シナリオ1",
          "ダミー攻撃シナリオ2",
          "ダミー攻撃シナリオ3",
          "ダミー攻撃シナリオ4",
          "ダミー攻撃シナリオ5",
          "ダミー攻撃シナリオ6",
          "ダミー攻撃シナリオ7",
          "ダミー攻撃シナリオ8",
          "ダミー攻撃シナリオ9",
          "ダミー攻撃シナリオ10"
        ]
      }.to_json
    else
      # エンティティ生成のリクエストの場合（EntityFormat）
      {
        "entities": [
          "entity1",
          "entity2"
        ],
        "summaries": [
          "summary1",
          "summary2"
        ]
      }.to_json
    end
  end
end
