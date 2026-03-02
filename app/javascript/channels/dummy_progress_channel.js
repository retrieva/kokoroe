import consumer from "channels/consumer"

export function subscribeDummyProgress(jobId, callbacks = {}) {
  return consumer.subscriptions.create({ channel: "DummyProgressChannel", job_id: jobId }, {
    connected() {
      // Called when the subscription is ready for use on the server
      if (callbacks.connected) {
        callbacks.connected();
      }
    },

    disconnected() {
      // Called when the subscription has been terminated by the server
      if (callbacks.disconnected) {
        callbacks.disconnected();
      }
    },

    received(data) {
      // Called when there's incoming data on the websocket for this channel
      if (callbacks.received) {
        callbacks.received(data);
      }
    }
  });
}
