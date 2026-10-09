"""What a new password must have (BRD G1).

The same rules are shown as a checklist on the registration screen
(frontend/src/features/auth/passwordRules.ts), so a refusal never surprises anyone.
Saying which rule failed reveals nothing about other accounts, unlike saying an email
is taken, which stays generic (G4).
"""

MIN_LENGTH = 8

COMMON = frozenset({"password", "12345678", "qwertyui", "admin123", "password123", "qwerty123"})
"""Passwords that meet every rule and are still the first anyone tries."""


def password_problems(password: str) -> list[str]:
    """What the password lacks, in words a person can act on; empty when it is fine."""
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"at least {MIN_LENGTH} characters")
    if not any(c.isalpha() for c in password):
        problems.append("a letter")
    if not any(c.isdigit() for c in password):
        problems.append("a digit")
    if all(c.isalnum() for c in password):
        problems.append("a special character such as @, ! or #")
    if password.lower() in COMMON:
        problems.append("not to be a common password")
    return problems
