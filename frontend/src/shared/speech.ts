/**
 * Speech turned into text by the browser itself (F21.2, ADR-0025): free, and no recording
 * ever reaches this service — only the text does. The browser's own recogniser may run on
 * its maker's servers (Chrome sends the sound to Google). Chrome, Edge and Safari have it;
 * where a browser does not, `listen` returns null and no microphone is offered.
 */

interface RecognitionResult {
  readonly isFinal: boolean;
  readonly 0: { readonly transcript: string };
}

interface RecognitionEvent {
  readonly resultIndex: number;
  readonly results: ArrayLike<RecognitionResult>;
}

interface Recognition {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: RecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type RecognitionConstructor = new () => Recognition;

const LOCALES: Record<string, string> = { en: "en-GB", uk: "uk-UA", pl: "pl-PL" };

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

function recognitionClass(): RecognitionConstructor | null {
  const w = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Whether this browser can turn speech into text. */
export function canListen(): boolean {
  return typeof window !== "undefined" && recognitionClass() !== null;
}

/**
 * Listen in `language` and report the words as they come (`onText`, `final` once a phrase
 * is done) until stopped or silent; returns the function that stops it.
 */
export function listen(
  language: string,
  onText: (text: string, final: boolean) => void,
  onEnd: () => void,
): (() => void) | null {
  const Recognition = recognitionClass();
  if (!Recognition) return null;
  const recognition = new Recognition();
  recognition.lang = LOCALES[language] ?? language;
  recognition.interimResults = true;
  recognition.continuous = false;
  let heard = "";
  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      if (!result) continue;
      if (result.isFinal) heard += result[0].transcript;
      else interim += result[0].transcript;
    }
    onText((heard + interim).trim(), interim === "");
  };
  recognition.onend = onEnd;
  recognition.onerror = onEnd;
  recognition.start();
  return () => {
    recognition.stop();
  };
}

/** Whether what was said is "approve", in any of the product's languages (F21.7). */
export function isApproval(text: string): boolean {
  return APPROVALS.has(text.trim().toLowerCase().replace(/[.!?]/g, ""));
}
