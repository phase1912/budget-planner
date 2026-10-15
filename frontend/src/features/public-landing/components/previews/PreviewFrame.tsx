import type { ReactNode } from "react";

/**
 * The frame a landing preview sits in: a card lifted off the page, like a screen of the
 * app. Decorative — what it shows is said in the text beside it — so assistive technology
 * skips it rather than reading sample figures as if they were the visitor's (F17.2).
 */
export function PreviewFrame({ children }: { children: ReactNode }) {
  return (
    <figure
      aria-hidden="true"
      className="m-0 w-full max-w-[420px] justify-self-center rounded-card border border-border bg-background p-4 shadow-card md:p-5"
    >
      {children}
    </figure>
  );
}
