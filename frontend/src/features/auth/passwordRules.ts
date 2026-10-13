/**
 * What a new password must have (BRD G1), mirrored from the server's
 * backend/app/domain/passwords.py so the checklist and the refusal never disagree.
 */
export interface PasswordRule {
  /** The rule's key under `auth:password` (F9.9). */
  label: "length" | "letter" | "digit" | "special" | "common";
  met: (password: string) => boolean;
}

const COMMON = new Set([
  "password",
  "12345678",
  "qwertyui",
  "admin123",
  "password123",
  "qwerty123",
]);

export const PASSWORD_RULES: PasswordRule[] = [
  { label: "length", met: (p) => p.length >= 8 },
  { label: "letter", met: (p) => /\p{L}/u.test(p) },
  { label: "digit", met: (p) => /\p{Nd}/u.test(p) },
  { label: "special", met: (p) => /[^\p{L}\p{N}]/u.test(p) },
  { label: "common", met: (p) => p === "" || !COMMON.has(p.toLowerCase()) },
];

/** Whether the password meets every rule. */
export function passwordIsValid(password: string): boolean {
  return PASSWORD_RULES.every((rule) => rule.met(password));
}
