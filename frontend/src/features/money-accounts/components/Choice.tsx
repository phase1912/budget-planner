/**
 * Two to four mutually exclusive options shown as cards side by side — "from outside or
 * from our other account", a tax rate — where a segmented control would be too cramped
 * for the labels. Each option is a radio, the group is labelled.
 */
export function Choice<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-md font-semibold text-muted-foreground">{label}</span>
      <div
        role="radiogroup"
        aria-label={label}
        className={`grid gap-2 ${options.length > 2 ? "grid-cols-2 md:grid-cols-4" : "grid-cols-2"}`}
      >
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={value === option.value}
            onClick={() => {
              onChange(option.value);
            }}
            className={`min-h-11 rounded-control border px-3 text-md font-semibold ${
              value === option.value ? "border-primary bg-tone-primary-bg" : "border-border"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
