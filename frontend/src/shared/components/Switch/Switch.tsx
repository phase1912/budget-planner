export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  /** Read out when there is no visible label, as in a Settings row whose title says it. */
  ariaLabel?: string;
  hint?: string;
  disabled?: boolean;
  id?: string;
}

export function Switch({ checked, onChange, label, ariaLabel, hint, disabled, id }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      id={id}
      aria-checked={checked}
      aria-label={label ? undefined : ariaLabel}
      disabled={disabled}
      onClick={() => {
        onChange(!checked);
      }}
      className={`flex min-h-11 items-center justify-between gap-4 text-left disabled:opacity-60 ${label ? "min-h-14 w-full" : ""}`}
    >
      {label && (
        <span className="flex flex-col gap-0.5">
          <span className="text-lg font-bold text-foreground">{label}</span>
          {hint && <span className="text-sm leading-relaxed text-muted-foreground">{hint}</span>}
        </span>
      )}
      <span
        aria-hidden="true"
        className={`flex h-7.5 w-12.5 shrink-0 items-center rounded-pill p-0.75 transition-colors ${
          checked ? "justify-end bg-primary" : "justify-start bg-border-strong"
        }`}
      >
        <span className="h-6 w-6 rounded-pill bg-background shadow-raised" />
      </span>
    </button>
  );
}
