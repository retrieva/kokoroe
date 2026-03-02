module ApplicationHelper
  include Pagy::Frontend

  def format_duration(seconds)
    return nil if seconds.nil?

    if seconds >= 3600
      hours = (seconds / 3600).floor
      minutes = ((seconds % 3600) / 60).ceil
      if minutes > 0
        "#{hours}時間#{minutes}分"
      else
        "#{hours}時間"
      end
    elsif seconds >= 60
      minutes = (seconds / 60).floor
      secs = (seconds % 60).ceil
      if secs > 0
        "#{minutes}分#{secs}秒"
      else
        "#{minutes}分"
      end
    else
      "#{seconds.ceil}秒"
    end
  end

  def new_badge(time)
    return unless time > 30.minutes.ago

    content_tag(:span, "new", class: "badge bg-warning text-dark ms-1")
  end

  def markdown(text)
    return "" if text.blank?

    renderer = Redcarpet::Render::HTML.new(
      hard_wrap: true,
      link_attributes: { target: "_blank", rel: "noopener noreferrer" }
    )
    markdown_parser = Redcarpet::Markdown.new(
      renderer,
      autolink: true,
      tables: true,
      fenced_code_blocks: true,
      strikethrough: true
    )
    sanitize(markdown_parser.render(text))
  end
end
