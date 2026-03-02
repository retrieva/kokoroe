class Attack::Example < ApplicationRecord
  self.table_name = "attack_examples"

  belongs_to :detail, class_name: "Attack::Detail", foreign_key: "attack_detail_id", inverse_of: :examples, touch: true

  validates :text, presence: true, allow_blank: false

  def as_json(_options = {})
    text
  end

  def empty?
    text.blank?
  end
end
