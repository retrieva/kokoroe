require 'rails_helper'

RSpec.describe Attack::ExecutionClient, type: :model do
  describe '.call_attack' do
    let(:scenario_hash) do
      {
        "name" => "test_scenario",
        "details" => [
          {
            "category" => "Hate/Hate-Speech/Race",
            "description" => "Test description",
            "severity" => "high"
          }
        ]
      }
    end

    context 'USE_DUMMY_ATTACKがtrueの場合' do
      before do
        allow(ENV).to receive(:[]).and_call_original
        allow(ENV).to receive(:[]).with('USE_DUMMY_ATTACK').and_return('true')
        described_class.force_next_failure = false
      end

      it 'ダミーレスポンスを期待される構造で返す' do
        result = described_class.call_attack(scenario_hash)

        expect(result).to be_a(Hash)
        expect(result).to have_key(:response)

        response = result[:response]
        expect(response).to have_key("overall-summary")
        expect(response).to have_key("quantitative-summary")
        expect(response).to have_key("qualitative-summary")
        expect(response).to have_key("other-stats")
      end

      it '定量的サマリーのデータを含む' do
        result = described_class.call_attack(scenario_hash)
        quantitative = result[:response]["quantitative-summary"]

        expect(quantitative).to have_key("Hate/Hate-Speech/Race")
        # アンダースコア形式のキー（実際のダミーレスポンスに合わせる）
        expect(quantitative["Hate/Hate-Speech/Race"]).to include(
          "number_of_successes" => 2,
          "number_of_attacks" => 4,
          "success_rate" => 0.5
        )
      end

      it '定性的サマリーに例を含む' do
        result = described_class.call_attack(scenario_hash)
        qualitative = result[:response]["qualitative-summary"]

        # アンダースコア形式のキー（実際のダミーレスポンスに合わせる）
        expect(qualitative["Hate/Hate-Speech/Race"]).to have_key("attack_success_examples")
        expect(qualitative["Hate/Hate-Speech/Race"]["attack_success_examples"]).to be_an(Array)
      end

      it 'other-statsに生成されたサンプルを含む' do
        result = described_class.call_attack(scenario_hash)
        samples = result[:response]["other-stats"]["generated-samples"]

        expect(samples).to be_an(Array)
        expect(samples.first).to include("prompt", "category", "response", "evaluation")
      end
    end

    context 'USE_DUMMY_ATTACKがfalseの場合' do
      before do
        allow(ENV).to receive(:[]).and_call_original
        allow(ENV).to receive(:[]).with('USE_DUMMY_ATTACK').and_return('false')
      end

      it '本番攻撃を実行しようとする（python3がない場合はエラー）' do
        result = described_class.call_attack(scenario_hash)

        expect(result).to be_a(Hash)
        # python3がない環境ではエラーになる
        expect(result[:status]).to eq('error')
      end
    end

    context 'USE_DUMMY_ATTACKが設定されていない場合' do
      before do
        allow(ENV).to receive(:[]).and_call_original
        allow(ENV).to receive(:[]).with('USE_DUMMY_ATTACK').and_return(nil)
      end

      it 'デフォルトで本番攻撃を実行しようとする（python3がない場合はエラー）' do
        result = described_class.call_attack(scenario_hash)

        expect(result).to be_a(Hash)
        # python3がない環境ではエラーになる
        expect(result[:status]).to eq('error')
      end
    end
  end
end
