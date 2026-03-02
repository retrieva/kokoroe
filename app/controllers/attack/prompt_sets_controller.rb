class Attack::PromptSetsController < ApplicationController
  before_action :set_scenario, only: [ :create ]
  before_action :set_prompt_set, only: [ :show, :destroy, :download ]

  def uncompleted
    prompt_sets = Attack::PromptSet.uncompleted.includes(:scenario)

    @pagy, @prompt_sets = pagy(prompt_sets.order(created_at: :desc))
  end

  def index
    @scenarios = Attack::Scenario.order(:name)

    prompt_sets = Attack::PromptSet.includes(:scenario)

    # シナリオで絞り込み
    if params[:scenario_id].present?
      prompt_sets = prompt_sets.where(attack_scenario_id: params[:scenario_id])
    end

    @pagy, @prompt_sets = pagy(prompt_sets.order(created_at: :desc))
  end

  def show
  end

  def create
    # プロンプト集を作成（after_create_commitでJobが自動実行される）
    name = params[:name].presence || @scenario.default_prompt_set_name
    prompt_set = @scenario.prompt_sets.create!(name: name)

    time_estimate = @scenario.estimated_prompt_generation_time
    notice_message = "プロンプト集の生成を開始しました。"
    notice_message += "（予想所要時間: #{time_estimate}）" if time_estimate

    redirect_to attack_prompt_set_path(prompt_set),
                notice: notice_message
  end

  def destroy
    unless @prompt_set.deletable?
      redirect_to attack_prompt_set_path(@prompt_set),
                  alert: @prompt_set.undeletable_reason
      return
    end

    scenario = @prompt_set.scenario
    @prompt_set.destroy!

    if params[:redirect_to] == "parent" && scenario
      redirect_to attack_scenario_path(scenario), notice: "プロンプト集を削除しました。"
    else
      redirect_to attack_prompt_sets_path, notice: "プロンプト集を削除しました。"
    end
  end

  def download
    prompts = @prompt_set.prompts.ordered

    csv_data = generate_csv(prompts)
    filename = "#{@prompt_set.name}.csv"

    send_data csv_data,
              filename: filename,
              type: "text/csv; charset=utf-8"
  end

  private

  def generate_csv(prompts)
    require "csv"

    # BOM付きUTF-8（Excel対応）
    bom = "\uFEFF"

    csv_string = CSV.generate do |csv|
      csv << [ "カテゴリ", "プロンプト" ]
      prompts.each do |prompt|
        csv << [ prompt.category, prompt.text ]
      end
    end

    bom + csv_string
  end

  def set_scenario
    @scenario = Attack::Scenario.find(params[:scenario_id])
  end

  def set_prompt_set
    @prompt_set = Attack::PromptSet.includes(:scenario, :prompts).find(params[:id])
  end
end
