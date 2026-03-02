import { Controller } from "@hotwired/stimulus"

// 折りたたみ時にスクロールするコントローラー
export default class extends Controller {
  static values = { target: String }

  connect() {
    this.boundScrollToTarget = this.scrollToTarget.bind(this)
    this.element.addEventListener("hide.bs.collapse", this.boundScrollToTarget)
  }

  disconnect() {
    this.element.removeEventListener("hide.bs.collapse", this.boundScrollToTarget)
  }

  scrollToTarget() {
    const targetElement = document.getElementById(this.targetValue)
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }
}
