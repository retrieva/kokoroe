class Attack::Prompt < ApplicationRecord
  belongs_to :prompt_set, class_name: "Attack::PromptSet", foreign_key: :attack_prompt_set_id, inverse_of: :prompts

  validates :category, presence: true
  validates :text, presence: true

  scope :in_category, ->(category) { where(category: category) }
  scope :ordered, -> { order(:position, :id) }
end
