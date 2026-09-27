import { Link, useLocation } from "react-router-dom";

const SECTIONS = [
  { name: "Receipts", path: "/receipts" },
  { name: "Categories", path: "/categories" },
] as const;

/**
 * "Receipts | Categories" at the top of both screens on a phone.
 *
 * The phone's bottom bar has room for one of them (docs/design/README.md), so
 * its Receipts tab stands for both and this switch makes the other one plain to
 * see, rather than a link lost under the title. Wider screens have both in the
 * header already.
 */
export function SectionTabs() {
  const { pathname } = useLocation();
  return (
    <nav
      aria-label="Receipts and categories"
      className="flex w-full gap-1 rounded-control border border-border bg-muted p-1 md:hidden"
    >
      {SECTIONS.map((section) => {
        const active = pathname === section.path || pathname.startsWith(`${section.path}/`);
        return (
          <Link
            key={section.path}
            to={section.path}
            aria-current={active ? "page" : undefined}
            className={`flex min-h-11 flex-1 items-center justify-center rounded-chip text-lg font-semibold transition-colors ${
              active
                ? "bg-background text-foreground shadow-raised"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {section.name}
          </Link>
        );
      })}
    </nav>
  );
}
