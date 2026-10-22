/**
 * Speech for the assistant (F21.2.2, ADR-0031): the microphone is recorded here as a WAV of
 * 16 kHz mono — a format every recogniser takes and every browser can make — and sent to
 * the service, which has Google Cloud recognise it and keeps nothing of the sound. A
 * minute at most; it stops by itself then.
 */

const RATE = 16000;
/** The longest recording, in seconds: the service refuses more. */
export const MAX_SECONDS = 60;

/** "Approve" as people say it in the product's languages (F21.7). */
const APPROVALS = new Set([
  "approve",
  "save",
  "yes",
  "підтвердити",
  "підтверджую",
  "зберегти",
  "так",
  "zatwierdź",
  "zatwierdzam",
  "zapisz",
  "tak",
]);

/** A recording in progress: `stop` ends it and gives the sound, `cancel` drops it. */
export interface Recording {
  stop: () => Promise<Blob>;
  cancel: () => void;
}

/** Whether this browser can record the microphone at all. */
export function canRecord(): boolean {
  return (
    typeof navigator !== "undefined" &&
    // Absent outside a secure page (https or localhost), whatever the types say.
    "mediaDevices" in navigator &&
    typeof navigator.mediaDevices.getUserMedia === "function" &&
    typeof window.AudioContext === "function" &&
    typeof window.AudioWorkletNode === "function"
  );
}

/**
 * Start recording the microphone; asks for permission the first time. `onLimit` runs when
 * the minute is up, for the caller to stop it. Rejects when the user refuses the
 * microphone or there is none.
 */
export async function record(onLimit: () => void): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const context = new AudioContext();
  // The worklet is a file of its own in public/: an audio thread loads it by address.
  await context.audioWorklet.addModule("/recorder-worklet.js");
  const source = context.createMediaStreamSource(stream);
  const processor = new AudioWorkletNode(context, "recorder");
  const chunks: Float32Array[] = [];
  processor.port.onmessage = (event: MessageEvent<Float32Array>) => {
    chunks.push(event.data);
  };
  source.connect(processor);
  processor.connect(context.destination);
  const limit = window.setTimeout(onLimit, MAX_SECONDS * 1000);

  const end = () => {
    window.clearTimeout(limit);
    processor.port.onmessage = null;
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((track) => {
      track.stop();
    });
    void context.close();
  };
  return {
    stop: () => {
      end();
      return Promise.resolve(wav(downsample(join(chunks), context.sampleRate)));
    },
    cancel: end,
  };
}

function join(chunks: Float32Array[]): Float32Array {
  const all = new Float32Array(chunks.reduce((n, c) => n + c.length, 0));
  let at = 0;
  for (const chunk of chunks) {
    all.set(chunk, at);
    at += chunk.length;
  }
  return all;
}

/** The sound at 16 kHz, each new sample the average of the ones it stands for. */
function downsample(samples: Float32Array, rate: number): Float32Array {
  if (rate <= RATE) return samples;
  const ratio = rate / RATE;
  const out = new Float32Array(Math.floor(samples.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const from = Math.floor(i * ratio);
    const to = Math.min(Math.floor((i + 1) * ratio), samples.length);
    let sum = 0;
    for (let j = from; j < to; j++) sum += samples[j] ?? 0;
    out[i] = sum / Math.max(to - from, 1);
  }
  return out;
}

/** 16-bit PCM WAV of mono samples at 16 kHz. */
function wav(samples: Float32Array): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const text = (at: number, value: string) => {
    for (let i = 0; i < value.length; i++) view.setUint8(at + i, value.charCodeAt(i));
  };
  text(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, RATE, true);
  view.setUint32(28, RATE * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  text(36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((sample, i) => {
    const clipped = Math.max(-1, Math.min(1, sample));
    view.setInt16(44 + i * 2, clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff, true);
  });
  return new Blob([buffer], { type: "audio/wav" });
}

/** Whether what was said is "approve", in any of the product's languages (F21.7). */
export function isApproval(text: string): boolean {
  return APPROVALS.has(text.trim().toLowerCase().replace(/[.!?]/g, ""));
}
