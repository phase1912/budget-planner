/** The viewer is always the primary colour; the others take the next ones in turn. */
const OTHERS = ["var(--cat-dining)", "var(--cat-entertainment)", "var(--cat-health)"];

/**
 * A colour per household member, the same on every family chart (F12.5, F12.9): the
 * viewer first in the primary colour, the others in the order given.
 */
export function memberColours(
  memberIds: readonly string[],
  me: string | undefined,
): Map<string, string> {
  const others = memberIds.filter((id) => id !== me);
  return new Map([
    ...(me && memberIds.includes(me) ? [[me, "var(--color-primary)"] as const] : []),
    ...others.map((id, i) => [id, OTHERS[i % OTHERS.length] ?? "var(--cat-other)"] as const),
  ]);
}
