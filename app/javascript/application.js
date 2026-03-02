// Configure your import map in config/importmap.rb. Read more: https://github.com/rails/importmap-rails
import "@hotwired/turbo-rails"
import "controllers"
import "@popperjs/core"
import "bootstrap"
import "channels"
import { subscribeDummyProgress } from "channels/dummy_progress_channel"
import "chartkick"
import "Chart.bundle"

import * as ActionCable from '@rails/actioncable'

ActionCable.logger.enabled = true

document.addEventListener("turbo:load", () => {
    document.querySelectorAll(".js-job-progress").forEach((el) => {
        const jobId = el.getAttribute("data-job-id")
        subscribeDummyProgress(jobId, {
            received(data) {
                console.log(data)
                if (data["progress_percentage"] !== undefined) {
                    // プログレスバーとパーセンテージテキストを更新
                    const progressBar = el.querySelector('.progress-bar')
                    const progressText = el.querySelector('.progress-text')
                    
                    progressBar.style.width = `${data["progress_percentage"]}%`
                    progressBar.setAttribute('aria-valuenow', data["progress_percentage"])
                    progressText.textContent = `${data["progress_percentage"]}%`
                    
                    if (data["progress_percentage"] >= 100) {
                        document.querySelectorAll(".js-next-action").forEach((el) => {
                            el.style.display = "block"
                        })
                        // TBD WebSocketを切断したい。ページから抜けたときも同様
                    }
                }
            },
        })
    })
})
