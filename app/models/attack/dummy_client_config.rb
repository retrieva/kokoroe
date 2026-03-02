module Attack
  module DummyClientConfig
    # ダミークライアントの進捗更新間隔（秒）
    # テスト環境: 0秒（即座に完了）
    # 開発環境: 1秒（進捗を確認できる速度）
    def self.progress_sleep_duration
      Rails.env.test? ? 0 : 1
    end
  end
end
