import { Controller } from "@hotwired/stimulus"

// トップに戻るボタンのコントローラー
export default class extends Controller {
  scrollToTop(event) {
    event.preventDefault()
    window.scrollTo({ top: 0, behavior: "smooth" })
  }
}
