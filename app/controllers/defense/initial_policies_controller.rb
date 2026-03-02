class Defense::InitialPoliciesController < ApplicationController
  before_action :set_policy, only: [ :show, :edit, :update, :destroy ]

  def index
    @policies = Defense::Policy.initial.order(created_at: :desc)
  end

  def show
  end

  def new
    @policy = Defense::Policy.new
  end

  def create
    @policy = Defense::Policy.new(policy_params)
    @policy.status = :completed  # 手動作成の初期方針は完了状態

    if @policy.save
      redirect_to defense_initial_policy_path(@policy), notice: "初期防衛方針が作成されました。"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
  end

  def update
    if @policy.update(policy_params)
      redirect_to defense_initial_policy_path(@policy), notice: "初期防衛方針が更新されました。"
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    if @policy.destroy
      redirect_to defense_initial_policies_path, notice: "初期防衛方針が削除されました。", status: :see_other
    else
      redirect_to defense_initial_policy_path(@policy), alert: @policy.errors.full_messages.to_sentence
    end
  end

  private

  def set_policy
    @policy = Defense::Policy.initial.find(params[:id])
  end

  def policy_params
    # contentsはテキストエリアから改行区切りで受け取り、配列に変換
    contents_text = params[:defense_policy][:contents_text] || ""
    contents_array = contents_text.split("\n").map(&:strip).reject(&:blank?)
    params[:defense_policy][:contents] = contents_array

    params.require(:defense_policy).permit(:name, contents: [])
  end
end
