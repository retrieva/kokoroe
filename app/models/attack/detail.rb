class Attack::Detail < ApplicationRecord
  self.table_name = "attack_details"

  belongs_to :scenario, class_name: "Attack::Scenario", foreign_key: "attack_scenario_id", inverse_of: :details, touch: true
  has_many :examples, class_name: "Attack::Example", foreign_key: "attack_detail_id", inverse_of: :detail, dependent: :destroy
  accepts_nested_attributes_for :examples, allow_destroy: true, reject_if: :all_blank

  before_validation :set_default_severity

  validates :category, presence: true, allow_blank: false, uniqueness: { scope: :attack_scenario_id }
  validates :description, presence: true, allow_blank: false
  validates :severity, presence: true, inclusion: { in: 1..5 }, allow_blank: false

  def as_json(options)
    super(only: [ :category, :description, :severity ]).merge(examples: examples.map { |e| e.as_json(options) })
  end

  def prepare_blank_example
    examples.build unless examples.any?(:empty?)
  end

  def empty?
    # marked_for_destructionでない例のみで判定
    active_examples = examples.reject(&:marked_for_destruction?)
    category.blank? && description.blank? && (active_examples.empty? || active_examples.all?(&:empty?))
  end

  def in_last_blank_category?
    active_details = scenario.details.reject(&:marked_for_destruction?)
    active_details.size > 1 && self == active_details.last && empty?
  end

  private

  def set_default_severity
    self.severity ||= 3
  end
end
