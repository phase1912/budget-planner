import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

export const Navigation = () => {
  const location = useLocation();
  const currentPath = location.pathname;
  const { t } = useTranslation();

  const links = [
    { name: t("nav.dashboard"), path: "/" },
    { name: t("nav.receipts"), path: "/receipts" },
    { name: t("nav.categories"), path: "/categories" },
    { name: t("nav.statistics"), path: "/statistics" },
    { name: t("nav.goals"), path: "/goals" },
  ];

  return (
    <nav className="flex items-center gap-[2px]">
      {links.map((link) => {
        // Both /categories and /categories/manage belong to the Categories item,
        // which every design screen draws as active on either.
        const isActive =
          link.path === "/"
            ? currentPath === "/"
            : currentPath === link.path || currentPath.startsWith(`${link.path}/`);
        return (
          <Link
            key={link.path}
            to={link.path}
            className={`px-3 py-2 rounded-control text-[14px] transition-colors ${
              isActive
                ? "bg-primary/10 text-primary font-semibold"
                : "text-muted-foreground hover:bg-surface-hover hover:text-foreground font-medium"
            }`}
          >
            {link.name}
          </Link>
        );
      })}
    </nav>
  );
};
