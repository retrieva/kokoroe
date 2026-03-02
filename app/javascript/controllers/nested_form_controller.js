import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["detailsContainer", "detail", "examplesContainer", "example"]
  static values = { scenarioId: String }

  connect() {
    console.log("Nested form controller connected")
    this.isComposing = false
  }

  handleCompositionStart() {
    this.isComposing = true
  }

  handleCompositionEnd(event) {
    this.isComposing = false
    // 変換確定後に適切なチェックを実行
    setTimeout(() => {
      // event.targetがexample fieldかdetail fieldかで判定
      if (event.target.name?.includes('[text]')) {
        this.checkExampleFields(event)
      } else {
        this.checkDetailFields()
      }
    }, 100)
  }

  checkDetailFields() {
    // IME変換中は処理をスキップ
    if (this.isComposing) return
    
    const details = this.detailTargets
    let emptyDetailCount = 0
    let needsServerCall = false
    
    console.log('=== checkDetailFields called ===')
    console.log('details count:', details.length)

    details.forEach(detail => {
      const category = detail.querySelector('input[name*="[category]"]')
      const description = detail.querySelector('textarea[name*="[description]"]')
      
      // detail のフィールドが空かチェック（severityは除外）
      const detailFieldsEmpty = (!category?.value || category.value.trim() === '') &&
                               (!description?.value || description.value.trim() === '')
      
      // example もすべて空かチェック
      const examplesContainer = detail.querySelector('[data-nested-form-target="examplesContainer"]')
      let allExamplesEmpty = true
      if (examplesContainer) {
        const examples = examplesContainer.querySelectorAll('[data-nested-form-target="example"]')
        examples.forEach(example => {
          const textInput = example.querySelector('input[type="text"]')
          if (textInput?.value && textInput.value.trim() !== '') {
            allExamplesEmpty = false
          }
        })
      }
      
      // detail が空 = detailのフィールドも空 かつ exampleもすべて空
      const isEmpty = detailFieldsEmpty && allExamplesEmpty
      
      console.log('Detail:', {
        category: category?.value,
        description: description?.value,
        detailFieldsEmpty,
        allExamplesEmpty,
        isEmpty
      })
      
      if (isEmpty) {
        emptyDetailCount++
      }

      // 同じdetail内で空のexampleの数もカウント（既に取得済み）
      if (examplesContainer) {
        const examples = examplesContainer.querySelectorAll('[data-nested-form-target="example"]')
        let emptyExampleCount = 0

        examples.forEach(example => {
          const textInput = example.querySelector('input[type="text"]')
          if (!textInput?.value || textInput.value.trim() === '') {
            emptyExampleCount++
          }
        })

        if (emptyExampleCount !== 1) {
          needsServerCall = true
        }
      }
    })

    // サーバーを呼ぶ条件：
    // 空のdetailが「ちょうど1つ」以外の場合
    // または、あるdetail内で空のexampleが「ちょうど1つ」以外の場合
    console.log('emptyDetailCount:', emptyDetailCount)
    console.log('needsServerCall:', needsServerCall)
    console.log('Will call server?', emptyDetailCount !== 1 || needsServerCall)
    
    if (emptyDetailCount !== 1 || needsServerCall) {
      this.autoAddDetail()
    }
  }

  checkExampleFields(event) {
    // IME変換中は処理をスキップ
    if (this.isComposing) return
    
    const examplesContainer = event.target.closest('[data-nested-form-target="examplesContainer"]')
    if (!examplesContainer) return

    const examples = examplesContainer.querySelectorAll('[data-nested-form-target="example"]')
    let emptyExampleCount = 0

    examples.forEach(example => {
      const textInput = example.querySelector('input[type="text"]')

      if (!textInput?.value || textInput.value.trim() === '') {
        emptyExampleCount++
      }
    })

    // サーバーを呼ぶ条件：
    // 1. 空のexampleがない場合（新しいexampleを追加）
    // 2. 空のexampleが2つ以上ある場合（余分なexampleを削除）
    if (examples.length > 0 && (emptyExampleCount === 0 || emptyExampleCount >= 2)) {
      const detailIndex = examplesContainer.dataset.detailIndex
      this.autoAddExample(detailIndex)
    }
  }

  autoAddDetail() {
    const url = this.scenarioIdValue === "new" 
      ? "/attack/scenarios/new/form" 
      : `/attack/scenarios/${this.scenarioIdValue}/form`

    const form = document.querySelector('form')
    if (!form) {
      console.error('Form not found')
      return
    }
    
    const formData = new FormData(form)
    
    fetch(url, {
      method: "PATCH",
      headers: {
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content,
        "Accept": "text/vnd.turbo-stream.html"
      },
      body: formData
    })
    .then(response => response.text())
    .then(html => {
      Turbo.renderStreamMessage(html)
    })
    .catch(error => {
      console.error('Error ensuring blank fields:', error)
    })
  }

  autoAddExample(detailIndex) {
    const url = this.scenarioIdValue === "new" 
      ? "/attack/scenarios/new/form" 
      : `/attack/scenarios/${this.scenarioIdValue}/form`

    const form = document.querySelector('form')
    if (!form) {
      console.error('Form not found')
      return
    }
    
    const formData = new FormData(form)
    formData.append("detail_index", detailIndex)
    
    fetch(url, {
      method: "PATCH",
      headers: {
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content,
        "Accept": "text/vnd.turbo-stream.html"
      },
      body: formData
    })
    .then(response => response.text())
    .then(html => {
      Turbo.renderStreamMessage(html)
    })
    .catch(error => {
      console.error('Error ensuring blank fields:', error)
    })
  }
}
