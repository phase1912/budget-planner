import * as React from "react";

export interface ModalProps extends React.HTMLAttributes<HTMLDivElement> {
  isOpen: boolean;
  onClose: () => void;
}

export const Modal = ({ isOpen, onClose, children, className, ...props }: ModalProps) => {
  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
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
