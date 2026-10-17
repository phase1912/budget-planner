import { ChevronLeft } from "lucide-react";
import { Link } from "react-router-dom";

export interface BackLinkProps {
  to: string;
  /** What the screen goes back to, read out in place of the arrow. */
  label: string;
}

/** The round "back" a screen opened from another tab carries above its title (design v2). */
export function BackLink({ to, label }: BackLinkProps) {
  return (
    <Link
      to={to}
      aria-label={label}
      className="control-fill flex h-11 w-11 shrink-0 items-center justify-center rounded-pill text-foreground"
    >
      <ChevronLeft size={20} aria-hidden="true" />
    </Link>
  );
}
