// The microphone's samples, handed to the page as they come (F21.2.2, `@/shared/speech`).
class Recorder extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel) this.port.postMessage(channel.slice(0));
    return true;
  }
}

registerProcessor("recorder", Recorder);
