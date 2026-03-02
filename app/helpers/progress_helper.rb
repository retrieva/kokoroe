module ProgressHelper
  # 進捗バーを更新するためのTurbo Streamをブロードキャスト
  def self.broadcast_progress(progress_id:, percentage:, status: nil, &block)
    dom_id = "progress_bar_#{progress_id}"

    if percentage >= 100
      # 100%になったら完了バッジに切り替え
      Turbo::StreamsChannel.broadcast_replace_to(
        "progress_#{progress_id}",
        target: dom_id,
        html: '<span class="badge bg-success">完了</span>'
      )
    else
      # 進捗バーを更新
      Turbo::StreamsChannel.broadcast_replace_to(
        "progress_#{progress_id}",
        target: dom_id,
        partial: "shared/progress_bar",
        locals: {
          dom_id: dom_id,
          percentage: percentage,
          status: status
        }
      )
    end

    block&.call(progress_id, percentage, status) # ブロックがあれば実行
  end

  # 開始日時を更新するためのTurbo Streamをブロードキャスト
  def self.broadcast_started_at(progress_id:, started_at:)
    started_at_content = if started_at
      I18n.l(started_at, format: :compact)
    else
      '<span class="text-muted">-</span>'
    end

    Turbo::StreamsChannel.broadcast_replace_to(
      "progress_#{progress_id}",
      target: "started_at_#{progress_id}",
      html: %(<div class="col-md-9" id="started_at_#{progress_id}">#{started_at_content}</div>)
    )
  end
end
