import * as React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "surface";
  flush?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = "default", flush = false, children, ...props }, ref) => {
    // Design v2: cards are flat on the palette's ground, the same surface either way;
    // `variant` stays for callers, a dialog's inset card being the only other use.
    const bgClass = variant === "surface" ? "bg-surface" : "bg-surface";
    const overflowClass = flush ? "overflow-hidden" : "";

    return (
      <div
        ref={ref}
        className={`on-surface rounded-card ${bgClass} ${overflowClass} ${className ?? ""}`}
        {...props}
      >
        {children}
      </div>
    );
  },
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={`bg-surface border-b border-border px-4.5 py-4 text-xl font-extrabold ${className ?? ""}`}
      {...props}
    />
  ),
);
CardHeader.displayName = "CardHeader";

export const CardBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={`px-4 py-4 md:px-6 md:py-5.5 ${className ?? ""}`} {...props} />
  ),
);
CardBody.displayName = "CardBody";

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={`bg-surface border-t border-border px-5 py-3.25 text-md ${className ?? ""}`}
      {...props}
    />
  ),
);
CardFooter.displayName = "CardFooter";
