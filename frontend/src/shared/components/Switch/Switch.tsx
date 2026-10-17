export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  hint?: string;
  disabled?: boolean;
  id?: string;
}

export function Switch({ checked, onChange, label, hint, disabled, id }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      id={id}
      aria-checked={checked}
      disabled={disabled}
      onClick={() => {
        onChange(!checked);
      }}
      className="flex min-h-14 w-full items-center justify-between gap-4 text-left disabled:opacity-60"
    >
      <span className="flex flex-col gap-0.5">
        <span className="text-lg font-semibold text-foreground">{label}</span>
        {hint && <span className="text-md leading-relaxed text-muted-foreground">{hint}</span>}
      </span>
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
