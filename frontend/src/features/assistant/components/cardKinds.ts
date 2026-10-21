/** The kinds of card the app draws with a card of its own; any other comes with a form. */
export const OWN_KINDS = ["budget", "income", "bill", "expense"] as const;
export type OwnKind = (typeof OWN_KINDS)[number];

/** Whether a card is one of the kinds the app draws with its own card. */
export function isOwn(kind: string): kind is OwnKind {
  return OWN_KINDS.some((own) => own === kind);
}
