import * as React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "surface";
  flush?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = "default", flush = false, children, ...props }, ref) => {
    const bgClass = variant === "surface" ? "bg-surface shadow-card" : "bg-background";
    const overflowClass = flush ? "overflow-hidden" : "";

    return (
      <div
        ref={ref}
        className={`border border-border rounded-card ${bgClass} ${overflowClass} ${className ?? ""}`}
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
      className={`bg-surface border-b border-border px-4.5 py-3.5 text-xl font-semibold ${className ?? ""}`}
      {...props}
    />
  ),
);
CardHeader.displayName = "CardHeader";

export const CardBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={`px-6 py-5.5 ${className ?? ""}`} {...props} />
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
