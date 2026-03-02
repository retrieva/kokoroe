class Attack::Scenario < ApplicationRecord
  self.table_name = "attack_scenarios"

  class InvalidJsonFormatError < StandardError; end

  has_many :details, class_name: "Attack::Detail", foreign_key: :attack_scenario_id, inverse_of: :scenario, dependent: :destroy, autosave: true
  has_many :prompt_sets, class_name: "Attack::PromptSet", foreign_key: :attack_scenario_id, dependent: :restrict_with_error

  accepts_nested_attributes_for :details, allow_destroy: true, reject_if: lambda { |attributes|
    attributes["id"].blank? &&
    attributes["category"].blank? &&
    attributes["description"].blank? &&
    (attributes["examples_attributes"].blank? || attributes["examples_attributes"].all? { |_, e| e["text"].blank? })
  }

  validates :name, presence: true
  validate :at_least_one_detail_required
  after_save :update_cycle_updated_at

  def self.from_json(json_data)
    raise InvalidJsonFormatError, "JSONデータは配列である必要があります" unless json_data.is_a?(Array)

    details_attributes = json_data.map.with_index do |detail, index|
      raise InvalidJsonFormatError, "#{index + 1}番目の要素がオブジェクトではありません" unless detail.is_a?(Hash)
      raise InvalidJsonFormatError, "#{index + 1}番目の要素にcategoryが含まれていません" unless detail["category"].present?
      raise InvalidJsonFormatError, "#{index + 1}番目の要素にdescriptionが含まれていません" unless detail["description"].present?

      examples_attributes = []
      if detail["examples"].present?
        raise InvalidJsonFormatError, "#{index + 1}番目の要素のexamplesが配列ではありません" unless detail["examples"].is_a?(Array)
        examples_attributes = detail["examples"].map.with_index do |example_text, ex_index|
          raise InvalidJsonFormatError, "#{index + 1}番目の要素の#{ex_index + 1}番目のexampleが文字列ではありません" unless example_text.is_a?(String)
          { text: example_text }
        end
      end

      {
        category: detail["category"],
        description: detail["description"],
        severity: detail["severity"],
        examples_attributes: examples_attributes
      }
    end

    new(details_attributes: details_attributes)
  end

  def human_name
    "#{self.class.model_name.human}「#{name}」"
  end

  # プロンプト集のデフォルト名
  def default_prompt_set_name
    "#{name}のプロンプト集"
  end

  # 削除可能かどうか
  def deletable?
    prompt_sets.empty?
  end

  # 削除できない理由
  def undeletable_reason
    return "プロンプト集があるため削除できません。" if prompt_sets.exists?
    nil
  end

  ESTIMATED_MINUTES_PER_CATEGORY_FOR_PROMPT_GENERATION = 2

  def estimated_prompt_generation_time
    return nil if details.size <= 0
    "最大約#{details.size * ESTIMATED_MINUTES_PER_CATEGORY_FOR_PROMPT_GENERATION}分"
  end

  def summary
    return "定義なし" if details.empty?

    first_category = details.first.category
    if details.count >= 2
      "#{first_category} ほか #{details.count - 1}件"
    else
      first_category
    end
  end

  def as_json(options = {})
    details.map { |d| d.as_json(options) }
  end

  def prepare_blank_detail
    # marked_for_destructionでない詳細のみで判定
    active_details = details.reject(&:marked_for_destruction?)
    details.build.prepare_blank_example unless active_details.any?(&:empty?)
  end

  def prepare_blank_detail_and_examples
    # 既存 detail の example を確保（marked_for_destructionでないもののみ）
    details.each do |detail|
      next if detail.marked_for_destruction?
      detail.prepare_blank_example
    end

    # 新しい空の detail を追加
    prepare_blank_detail
  end

  def remove_blank_details
    # 1. まず examples を処理（detailの判定に影響するため先に処理）
    details.each do |detail|
      next if detail.marked_for_destruction?

      detail.examples.each do |example|
        next if example.marked_for_destruction?
        next unless example.empty?

        if example.persisted?
          # 既存の例: 削除マークを付ける
          example.mark_for_destruction
        else
          # 未保存の例: 関連から即座に削除
          detail.examples.delete(example)
        end
      end
    end

    # 2. 次に details を処理（exampleの削除が反映された状態で判定）
    details.each do |detail|
      next if detail.marked_for_destruction?
      next unless detail.empty?

      if detail.persisted?
        # 既存の詳細: 削除マークを付ける（DB削除は更新ボタン押下時まで延期）
        detail.mark_for_destruction
      else
        # 未保存の詳細: 関連から即座に削除
        details.delete(detail)
      end
    end
  end

  private

  def at_least_one_detail_required
    # reject_ifでスキップされない有効なdetailが存在するかチェック
    active_details = details.reject(&:marked_for_destruction?)
    valid_details = active_details.reject(&:empty?)
    if valid_details.empty?
      errors.add(:base, "少なくとも1つのカテゴリを入力してください")
    end
  end

  def update_cycle_updated_at
    update_column(:cycle_updated_at, updated_at)
  end
end
