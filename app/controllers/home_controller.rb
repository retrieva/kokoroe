class HomeController < ApplicationController
  def index
    @recent_scenarios = Attack::Scenario.order(cycle_updated_at: :desc).limit(3)
    @recent_prompt_sets = Attack::PromptSet.order(cycle_updated_at: :desc).limit(3)
    @recent_executions = Attack::Execution.order(cycle_updated_at: :desc).limit(3)
    @recent_initial_policies = Defense::Policy.initial.order(cycle_updated_at: :desc).limit(3)
    @recent_policies = Defense::Policy.extended.order(cycle_updated_at: :desc).limit(3)
    @recent_training_datasets = Defense::TrainingDataset.order(created_at: :desc).limit(3)
  end

  def attack_scenarios_index
  end

  def attack_scenarios_show
  end

  def attack_prompt_collections_index
  end

  def attack_prompt_collections_show
  end

  def attacks_index
  end

  def attacks_show
  end

  def dummy_job
  end

  def dummy_python_job_new
    next_url = safe_url(params[:next_url])
    seconds = params[:seconds].to_i
    job = DummyPythonJob.perform_later(next_url: next_url, seconds: seconds)
    redirect_to jobs_progress_path(job_id: job.job_id)
  end

  def job_progress
    @job = SolidQueue::Job.find_by(active_job_id: params[:job_id])

    # ジョブの引数からnext_urlを取得
    @next_url = safe_url(@job.arguments["arguments"].first["next_url"])
  end

  def tbd
    @next_url = safe_url(params[:next_url])
  end

  private

  def safe_url(url)
    return nil if url.blank?

    # 相対URLのみを許可
    begin
      uri = URI.parse(url)

      # 相対URLの場合のみ許可
      return url if uri.relative?

      # 絶対URLの場合は拒否
      nil
    rescue URI::InvalidURIError
      # 無効なURLの場合はnilを返す
      nil
    end
  end
end
