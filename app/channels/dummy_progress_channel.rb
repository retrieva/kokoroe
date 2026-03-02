class DummyProgressChannel < ApplicationCable::Channel
  def subscribed
    stream_from "dummy_progress_#{params[:job_id]}"
  end

  def unsubscribed
    # Any cleanup needed when channel is unsubscribed
  end
end
