class Defense::ExtensionsController < ApplicationController
  before_action :set_policy, only: [ :destroy ]

  def index
    @source_policies = Defense::Policy.initial.completed.recent

    policies = Defense::Policy.extended.includes(:source_policy, :attack_execution)

    @source_policy = Defense::Policy.find_by(id: params[:source_policy_id])
    policies = policies.where(source_policy_id: @source_policy.id) if @source_policy

    if params[:status].present?
      policies = policies.where(status: params[:status])
    end

    @extensions = policies.recent
  end

  def uncompleted
    @source_policies = Defense::Policy.initial.completed.recent

    policies = Defense::Policy.extended.uncompleted.includes(:source_policy, :attack_execution)

    @source_policy = Defense::Policy.find_by(id: params[:source_policy_id])
    policies = policies.where(source_policy_id: @source_policy.id) if @source_policy

    if params[:status].present?
      policies = policies.where(status: params[:status])
    end

    @extensions = policies.recent
  end

  def create
    @source_policy = Defense::Policy.find(params[:source_policy_id])
    attack_execution = Attack::Execution.find(params[:attack_execution_id])

    # 新しい拡張方針を作成（pending状態、after_create_commitでジョブがキューされる）
    name = params[:name].presence || attack_execution.default_policy_name
    @policy = Defense::Policy.create!(
      name: name,
      source_policy: @source_policy,
      attack_execution: attack_execution
    )

    time_estimate = attack_execution.estimated_extension_time
    notice_message = "防衛方針の拡張を開始しました。"
    notice_message += "（予想所要時間: #{time_estimate}）" if time_estimate

    redirect_to defense_policy_path(@policy),
                notice: notice_message
  end

  def destroy
    @policy.destroy!
    redirect_to defense_extensions_path, notice: "拡張履歴を削除しました。"
  end

  private

  def set_policy
    @policy = Defense::Policy.includes(:source_policy, :attack_execution).find(params[:id])
  end
end
