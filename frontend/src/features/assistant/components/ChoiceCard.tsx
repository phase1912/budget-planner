import { useTranslation } from "react-i18next";

import type { ChatMessage } from "@/stores/AssistantStore";

/**
 * The assistant's question as options to tap (F21.13.3): when more than one thing fits
 * what the user said, or something is missing. A tap sends the option as the user's
 * answer; once the conversation has moved on, the options stay as a record and no longer
 * answer.
 */
export function ChoiceCard({
  message,
  answered,
  onChoose,
}: {
  message: ChatMessage;
  answered: boolean;
  onChoose: (option: string) => void;
}) {
  const { t } = useTranslation("assistant");
  const raw = message.card?.fields.options;
  const options = Array.isArray(raw) ? raw.filter((o): o is string => typeof o === "string") : [];

  return (
    <ul aria-label={t("choice")} className="m-0 flex list-none flex-wrap gap-2 p-0">
      {options.map((option) => (
        <li key={option} className="max-w-full">
          <button
            type="button"
            disabled={answered}
            onClick={() => {
              onChoose(option);
            }}
            className="min-h-11 max-w-full rounded-pill bg-tone-primary-bg px-4 text-left text-md font-bold break-words text-primary disabled:opacity-50"
          >
            {option}
          </button>
        </li>
      ))}
    </ul>
  );
}
