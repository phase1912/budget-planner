import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { ChevronRight, X } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Modal, ModalBody } from "@/shared/components";

/** A group of Settings rows under an uppercase label (design v2). */
export function SettingsGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2.5">
      <h2 className="m-0 px-1 text-md font-bold uppercase tracking-[0.06em] text-muted-foreground">
        {label}
      </h2>
      <ul className="m-0 flex list-none flex-col divide-y divide-border overflow-hidden rounded-card bg-surface p-0">
        {children}
      </ul>
    </section>
  );
}

export interface SettingsRowProps {
  icon: LucideIcon;
  /** A colour token for the icon tile, e.g. `var(--cat-dining)`. */
  color?: string;
  label: string;
  hint?: string;
  value?: ReactNode;
  /** What sits at the right instead of a value and a chevron, e.g. a switch. */
  aside?: ReactNode;
  onClick?: () => void;
  to?: string;
  danger?: boolean;
  id?: string;
}

/**
 * One Settings row: a tinted icon tile, a title with an optional hint, and its value with
 * a chevron when it opens something — or a control of its own at the right.
 */
export function SettingsRow({
  icon: Icon,
  color = "var(--color-primary)",
  label,
  hint,
  value,
  aside,
  onClick,
  to,
  danger = false,
  id,
}: SettingsRowProps) {
  const tint = danger ? "var(--color-error)" : color;
  const body = (
    <>
      <span
        aria-hidden="true"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-chip"
        style={{ background: `color-mix(in srgb, ${tint} 15%, transparent)`, color: tint }}
      >
        <Icon size={18} />
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className={`text-lg font-bold ${danger ? "text-error" : ""}`}>{label}</span>
        {hint && <span className="text-sm text-muted-foreground">{hint}</span>}
      </span>
      {aside ?? (
        <span className="flex min-w-0 shrink items-center gap-1 text-md font-semibold text-muted-foreground">
          {value !== undefined && <span className="truncate">{value}</span>}
          {(onClick ?? to) && <ChevronRight size={16} className="shrink-0" aria-hidden="true" />}
        </span>
      )}
    </>
  );
  const layout = "flex min-h-15 w-full items-center gap-3 px-4 py-2.5 text-left";
  return (
    <li id={id} className="scroll-mt-4">
      {to ? (
        <Link to={to} className={`${layout} text-foreground`}>
          {body}
        </Link>
      ) : onClick ? (
        <button type="button" onClick={onClick} className={layout}>
          {body}
        </button>
      ) : (
        <div className={layout}>{body}</div>
      )}
    </li>
  );
}

/** A Settings detail opened from a row: a dialog with a title and a close button. */
export function SettingsSheet({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <Modal isOpen onClose={onClose} className="w-full md:max-w-[520px]" aria-label={title}>
      <ModalBody className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="m-0 text-xl font-extrabold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("close")}
            className="flex h-11 w-11 items-center justify-center rounded-pill bg-muted text-foreground"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        {children}
      </ModalBody>
    </Modal>
  );
}
