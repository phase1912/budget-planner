import * as React from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export interface ModalProps extends React.HTMLAttributes<HTMLDivElement> {
  isOpen: boolean;
  onClose: () => void;
}

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-[4px] p-10">
      <div
        data-testid="backdrop"
        className="absolute inset-0"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        ref={dialogRef}
        tabIndex={-1}
        className={`relative z-10 flex flex-col overflow-hidden max-h-full border border-border rounded-card bg-background shadow-modal ${className ?? ""}`}
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
    className={`flex items-start justify-between gap-4 border-b border-border bg-surface px-6 py-5 ${className ?? ""}`}
    {...props}
  />
);
ModalHeader.displayName = "ModalHeader";

export const ModalBody = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={`flex-grow overflow-y-auto px-6 py-5 ${className ?? ""}`} {...props} />
);
ModalBody.displayName = "ModalBody";

export const ModalFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={`flex items-center justify-between gap-5 border-t border-border bg-surface px-6 py-[18px] ${className ?? ""}`}
    {...props}
  />
);
ModalFooter.displayName = "ModalFooter";
