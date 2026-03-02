class DummyPythonJob < ApplicationJob
  queue_as :default

  # TODO: seconds は現在利用していないが、将来的には全部消すため一旦残している
  def perform(next_url: nil, seconds: 0)
    # Do something later
    puts "will be exec python"
    puts "next_url: #{next_url}" if next_url
    puts "sleeping for #{seconds} seconds" if seconds > 0

    # Pythonプログラムを実際に実行
    if seconds.to_i > 0
      execute_python_script(seconds.to_i)
    end
  end

  private

  def execute_python_script(seconds)
    # python3コマンドの存在確認
    python_available = system("which python3 > /dev/null 2>&1")
    unless python_available
      puts "Error: python3 command not found"
      return
    end

    begin
      # IO.popenを使用してリアルタイムで出力を取得
      require "json"

      # auto-red-team-promptの適当なスクリプトを動作確認のために実行
      cmd = [
        "python3",
        "-u",
        "auto-red-team-prompt/scripts/run_generate_red_prompt.py",
        "--model_type", "vllm",
        # 開発用のためにこのRailsアプリ自身がホストしているダミーのAPIを叩く設定ファイルを指定している
        # 実際のAPIを叩く場合は ./config/auto-red-team-prompt/docker-online.json を指定するように変更する
        "--model_config_file", "./config/auto-red-team-prompt/rails-dummy-api.json",
        "--risk_json", "auto-red-team-prompt/target-risks/sample.json",
        "--output_path", "hoge.json",
        "--log-level", "INFO"
      ]
      IO.popen(cmd, err: [ :child, :out ]) do |io|
        io.each_line do |line|
          begin
            data = JSON.parse(line)
            # JSON形式の進捗データの場合
            if data["progress_percentage"]
              puts "Progress: #{data["progress_percentage"]}% (#{data["elapsed_seconds"]}/#{data["total_seconds"]}s) - #{data["status"]}"
              pp ActionCable.server.broadcast(
                "dummy_progress_#{job_id}",
                data
              )
            else
              puts "Python JSON: #{line.chomp}"
            end
          rescue JSON::ParserError
            # JSON以外の出力（通常のメッセージなど）
            puts "Python output: #{line.chomp}"
          end
        end
      end

      puts "Python script completed"
      # 実装途中のスクリプトが進捗を出力していないこともあるので、そういう場合でも次の画面に進めるように100%の進捗を送信しておく
      pp ActionCable.server.broadcast(
        "dummy_progress_#{job_id}",
        {
          progress_percentage: 100
        },
      )

    rescue => e
      puts "Error executing Python script: #{e.class}: #{e.message}"
      puts "Backtrace: #{e.backtrace.first(5).join("\n")}"
    end
  end
end
