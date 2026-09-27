import * as React from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export interface ModalProps extends React.HTMLAttributes<HTMLDivElement> {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * A dialog over the page, trapping focus until closed (Escape or the backdrop).
 *
 * A centred card at every size. On a phone it takes the full width but for a
 * small margin, so a dialog is never squeezed narrower than its content allows;
 * a caller sets its tablet and desktop width with `md:` classes.
 */
export const Modal = ({ isOpen, onClose, children, className, ...props }: ModalProps) => {
  const dialogRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!isOpen) return;

    // Remembered before focus moves into the dialog, so closing can put the
    // caret back where the user left it instead of at the top of the document.
    const previouslyFocused = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab") return;

      const focusable = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [],
      );
      if (focusable.length === 0) {
        e.preventDefault();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-[4px] p-3 md:p-10">
      <div
        data-testid="backdrop"
        className="absolute inset-0"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        ref={dialogRef}
        tabIndex={-1}
        className={`relative z-10 flex w-full flex-col overflow-hidden max-h-full border border-border rounded-card bg-background shadow-modal ${className ?? ""}`}
        role="dialog"
        aria-modal="true"
        {...props}
      >
        {children}
      </div>
    </div>
  );
};
Modal.displayName = "Modal";

export const ModalHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={`flex items-start justify-between gap-4 border-b border-border bg-surface px-4 py-4 md:px-6 md:py-5 ${className ?? ""}`}
    {...props}
  />
);
ModalHeader.displayName = "ModalHeader";

export const ModalBody = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={`flex-grow overflow-y-auto px-4 py-4 md:px-6 md:py-5 ${className ?? ""}`}
    {...props}
  />
);
ModalBody.displayName = "ModalBody";

export const ModalFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={`flex flex-wrap items-center justify-between gap-3 border-t border-border bg-surface px-4 py-3.5 md:flex-nowrap md:gap-5 md:px-6 md:py-[18px] ${className ?? ""}`}
    {...props}
  />
);
ModalFooter.displayName = "ModalFooter";
