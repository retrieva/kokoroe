class Defense::PoliciesController < ApplicationController
  before_action :set_policy, only: [ :show, :destroy ]

  def index
    @initial_policies = Defense::Policy.initial.order(:name)

    policies = Defense::Policy.extended.includes(:source_policy)

    # 初期防衛方針で絞り込み
    if params[:source_policy_id].present?
      policies = policies.where(source_policy_id: params[:source_policy_id])
    end

    @policies = policies.order(created_at: :desc)
  end

  def show
  end

  def destroy
    attack_execution = @policy.attack_execution

    if @policy.destroy
      path = params[:redirect_to] == "parent" && attack_execution ? attack_report_path(attack_execution) : defense_policies_path
      redirect_to path, notice: "防衛方針が削除されました。", status: :see_other
    else
      redirect_to defense_policy_path(@policy), alert: @policy.errors.full_messages.to_sentence
    end
  end

  private

  def set_policy
    @policy = Defense::Policy.extended.find(params[:id])
  end
end
