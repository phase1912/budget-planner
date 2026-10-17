import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

const PAGES = ["help", "privacy", "terms"] as const;

/**
 * Help, the privacy policy and the terms (F17.7.1), linked from the foot of every public
 * page, so a visitor can read them before signing up and anyone can find them again.
 */
export function PublicLinks({ className = "" }: { className?: string }) {
  const { t } = useTranslation();
  return (
    <nav
      aria-label={t("footer.label")}
      className={`flex flex-wrap justify-center gap-x-4 gap-y-1 ${className}`}
    >
      {PAGES.map((page) => (
        <Link
          key={page}
          to={`/${page}`}
          className="inline-flex min-h-11 items-center text-md text-muted-foreground underline-offset-2 hover:text-foreground hover:underline md:min-h-0"
        >
          {t(`footer.${page}`)}
        </Link>
      ))}
    </nav>
  );
}
