import type { ReactNode } from "react";

import { Card, PublicLinks } from "@/shared/components";

/** The centred card every signed-out account screen sits in (login.html). */
export function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex-grow flex flex-col items-center justify-center gap-6 py-10">
      <Card className="w-full max-w-md p-6 md:p-8 flex flex-col gap-6">
        <div className="text-center">
          <h1 className="text-xl font-semibold mb-2">{title}</h1>
          {subtitle && <p className="m-0 text-base text-muted-foreground">{subtitle}</p>}
        </div>
        {children}
      </Card>
      <PublicLinks />
    </div>
  );
}
