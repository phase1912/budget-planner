/**
 * What a new password must have (BRD G1), mirrored from the server's
 * backend/app/domain/passwords.py so the checklist and the refusal never disagree.
 */
export interface PasswordRule {
  label: string;
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
  { label: "At least 8 characters", met: (p) => p.length >= 8 },
  { label: "A letter", met: (p) => /\p{L}/u.test(p) },
  { label: "A digit", met: (p) => /\p{Nd}/u.test(p) },
  { label: "A special character, such as @, ! or #", met: (p) => /[^\p{L}\p{N}]/u.test(p) },
  { label: "Not a common password", met: (p) => p === "" || !COMMON.has(p.toLowerCase()) },
];

/** Whether the password meets every rule. */
export function passwordIsValid(password: string): boolean {
  return PASSWORD_RULES.every((rule) => rule.met(password));
}
