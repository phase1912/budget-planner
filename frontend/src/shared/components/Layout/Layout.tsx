import * as React from "react";

export interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "default" | "narrow" | "wide";
  /** False inside another container, whose side padding already applies. */
  gutter?: boolean;
}

export const Container = React.forwardRef<HTMLDivElement, ContainerProps>(
  ({ className, size = "default", gutter = true, ...props }, ref) => {
    let sizeClass = "max-w-default";
    if (size === "narrow") sizeClass = "max-w-narrow";
    if (size === "wide") sizeClass = "max-w-wide";

    return (
      <div
        ref={ref}
        className={`w-full mx-auto ${gutter ? "px-4 md:px-6 lg:px-8" : ""} ${sizeClass} ${className ?? ""}`}
        {...props}
      />
    );
  },
);
Container.displayName = "Container";

export const Stack = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    return <div ref={ref} className={`flex flex-col ${className ?? ""}`} {...props} />;
  },
);
Stack.displayName = "Stack";

export const Grid = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    return <div ref={ref} className={`grid ${className ?? ""}`} {...props} />;
  },
);
Grid.displayName = "Grid";
