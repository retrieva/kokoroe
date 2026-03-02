class Attack::ReportsController < ApplicationController
  before_action :set_prompt_set, only: [ :create ]
  before_action :set_execution, only: [ :show, :destroy ]

  def index
    executions = Attack::Execution.includes(prompt_set: :scenario)

    if params[:prompt_set_id].present?
      executions = executions.where(attack_prompt_set_id: params[:prompt_set_id])
    end

    @pagy, @executions = pagy(executions.order(created_at: :desc))
  end

  def uncompleted
    executions = Attack::Execution.uncompleted.includes(prompt_set: :scenario)
    @pagy, @executions = pagy(executions.order(created_at: :desc))
  end

  def show
    # 拡張フォーム用に初期方針を取得（完了時のみ使用）
    @initial_policies = Defense::Policy.initial.completed.recent if @execution.completed?
  end

  def create
    # 新しい攻撃を作成
    name = params[:name].presence || @prompt_set.default_execution_name
    execution = @prompt_set.executions.create!(name: name)

    time_estimate = @prompt_set.estimated_execution_time
    notice_message = "攻撃を開始しました。"
    notice_message += "（予想所要時間: #{time_estimate}）" if time_estimate

    redirect_to attack_report_path(execution),
                notice: notice_message
  end

  def destroy
    unless @execution.deletable?
      redirect_to attack_report_path(@execution),
                  alert: @execution.undeletable_reason
      return
    end

    prompt_set = @execution.prompt_set
    @execution.destroy!

    if params[:redirect_to] == "parent" && prompt_set
      redirect_to attack_prompt_set_path(prompt_set), notice: "攻撃結果レポートを削除しました。"
    else
      redirect_to attack_reports_path, notice: "攻撃結果レポートを削除しました。"
    end
  end

  private

  def set_prompt_set
    @prompt_set = Attack::PromptSet.find(params[:prompt_set_id])
  end

  def set_execution
    @execution = Attack::Execution.includes(prompt_set: :scenario).find(params[:id])
  end
end
