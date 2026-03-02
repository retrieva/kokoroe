class Attack::ScenariosController < ApplicationController
  before_action :set_scenario, only: [ :show, :edit, :update, :destroy, :download, :ensure_blank_fields_for_scenario ]
  before_action :set_new_scenario, only: [ :new, :ensure_blank_fields_for_new_scenario ]

  def index
    @scenarios = Attack::Scenario.includes(details: :examples).order(created_at: :desc)
  end

  def new
    @scenario.prepare_blank_detail_and_examples
  end

  def create
    @scenario = Attack::Scenario.new(scenario_params)

    if @scenario.save
      redirect_to attack_scenario_path(@scenario), notice: "#{@scenario.human_name}が作成されました。"
    else
      @scenario.prepare_blank_detail_and_examples
      render :new, status: :unprocessable_entity
    end
  end

  def show
  end

  def edit
    @scenario.prepare_blank_detail_and_examples
  end

  def update
    if @scenario.update(scenario_params)
      redirect_to attack_scenario_path(@scenario), notice: "#{@scenario.human_name}が更新されました。"
    else
      @scenario.prepare_blank_detail_and_examples
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    if @scenario.destroy
      redirect_to attack_scenarios_path, notice: "#{@scenario.human_name}が削除されました。", status: :see_other
    else
      redirect_to attack_scenario_path(@scenario), alert: @scenario.errors.full_messages.to_sentence
    end
  end

  def download
    send_data @scenario.to_json,
              filename: "#{@scenario.name}.json",
              type: "application/json",
              disposition: "attachment"
  end

  def new_import
  end

  def create_import
    file = params[:file]
    unless file.present?
      flash.now[:alert] = "ファイルを選択してください。"
      render :new_import
      return
    end

    begin
      # ファイル名から拡張子を除いた部分を取得
      filename = File.basename(file.original_filename, ".*")

      # JSONをパース
      json_data = JSON.parse(file.read)

      # シナリオを作成
      @scenario = Attack::Scenario.from_json(json_data)
      @scenario.name = filename

      if @scenario.save
        redirect_to attack_scenario_path(@scenario), notice: "#{@scenario.human_name}がインポートされました。"
      else
        flash.now[:alert] = "インポートに失敗しました: #{@scenario.errors.full_messages.join(', ')}"
        render :new_import
      end
    rescue Attack::Scenario::InvalidJsonFormatError => e
      flash.now[:alert] = e.message
      render :new_import
    rescue JSON::ParserError => e
      flash.now[:alert] = "JSONファイルの解析に失敗しました: #{e.message}"
      render :new_import
    end
  end

  def ensure_blank_fields_for_new_scenario
    ensure_blank_fields
  end

  def ensure_blank_fields_for_scenario
    ensure_blank_fields
  end

  private

  def ensure_blank_fields
    @scenario.assign_attributes(scenario_params)

    @scenario.remove_blank_details
    @scenario.prepare_blank_detail_and_examples

    respond_to do |format|
      format.turbo_stream {
        render turbo_stream: turbo_stream.replace("scenario-form",
          partial: "attack/scenarios/form",
          locals: {
            scenario: @scenario,
            url: @scenario.persisted? ? attack_scenario_path(@scenario) : attack_scenarios_path,
            submit_text: @scenario.persisted? ? "更新" : "作成",
            cancel_path: @scenario.persisted? ? attack_scenario_path(@scenario) : attack_scenarios_path
          },
          method: :morph)
      }
      format.html { render :edit }
    end
  end

  def set_scenario
    @scenario = Attack::Scenario.find(params[:id])
  end

  def set_new_scenario
    @scenario = Attack::Scenario.new
  end


  def build_empty_associations
    if @scenario.details.empty?
      detail = @scenario.details.build
      detail.examples.build
    else
      @scenario.details.each do |detail|
        detail.examples.build if detail.examples.empty?
      end
      detail = @scenario.details.build
      detail.examples.build
    end
  end

  def scenario_params
    params.require(:attack_scenario).permit(
      :name,
      details_attributes: [
        :id,
        :category,
        :description,
        :severity,
        :_destroy,
        examples_attributes: [ :id, :text, :_destroy ]
      ]
    )
  end
end
