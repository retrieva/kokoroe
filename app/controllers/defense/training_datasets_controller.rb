class Defense::TrainingDatasetsController < ApplicationController
  before_action :set_dataset, only: [ :show, :destroy, :download ]

  def index
    @policy_options = Defense::Policy.extended.completed.order(:name)

    datasets = Defense::TrainingDataset.includes(:policy)

    if params[:defense_policy_id].present?
      datasets = datasets.where(defense_policy_id: params[:defense_policy_id])
    end

    @pagy, @datasets = pagy(datasets.order(created_at: :desc))
  end

  def uncompleted
    datasets = Defense::TrainingDataset.uncompleted.includes(:policy)
    @pagy, @datasets = pagy(datasets.order(created_at: :desc))
  end

  def show
  end

  def create
    @policy = Defense::Policy.find(params[:defense_policy_id])

    @dataset = @policy.training_datasets.create!(
      attack_execution_id: params[:attack_execution_id],
      name: params[:name].presence || @policy.default_training_dataset_name
    )

    time_estimate = @policy.estimated_training_dataset_time
    notice_message = "学習データの生成を開始しました。"
    notice_message += "（予想所要時間: #{time_estimate}）" if time_estimate

    respond_to do |format|
      format.html do
        redirect_to defense_training_dataset_path(@dataset),
                    notice: notice_message
      end
      format.turbo_stream do
        @training_datasets = @policy.training_datasets.includes(:attack_execution).recent.limit(10)
        @attack_executions = Attack::Execution.completed.order(created_at: :desc)
        flash.now[:notice] = notice_message
      end
    end
  end

  def destroy
    unless @dataset.deletable?
      redirect_to defense_training_dataset_path(@dataset), alert: @dataset.undeletable_reason
      return
    end

    policy = @dataset.policy
    @dataset.destroy!

    if params[:redirect_to] == "parent" && policy
      redirect_to defense_policy_path(policy), notice: "学習データを削除しました。"
    else
      redirect_to defense_training_datasets_path, notice: "学習データを削除しました。"
    end
  end

  def download
    unless @dataset.completed?
      redirect_to defense_training_dataset_path(@dataset), alert: "学習データの生成が完了していません。"
      return
    end

    file_info = safe_file_path_for_download
    unless file_info
      redirect_to defense_training_dataset_path(@dataset), alert: "ファイルが見つかりません。"
      return
    end

    send_data File.read(file_info[:path]),
              filename: file_info[:filename],
              type: "application/json",
              disposition: "attachment"
  end

  private

  def safe_file_path_for_download
    file_path = case params[:format]
    when "sft"
      @dataset.sft_data_path
    when "dpo"
      @dataset.dpo_data_path
    when "report"
      @dataset.report_path
    end

    return nil unless file_path.present? && File.exist?(file_path)

    # ファイルパスが許可されたディレクトリ内にあることを検証
    allowed_dir = Rails.root.join("tmp", "training_datasets")
    real_path = Pathname.new(file_path).realpath.to_s
    return nil unless real_path.start_with?(allowed_dir.realpath.to_s)

    { path: real_path, filename: File.basename(real_path) }
  end

  def set_dataset
    @dataset = Defense::TrainingDataset.includes(:policy, :attack_execution).find(params[:id])
  end
end
