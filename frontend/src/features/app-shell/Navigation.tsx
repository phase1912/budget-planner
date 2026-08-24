import { Link, useLocation } from "react-router-dom";

export const Navigation = () => {
  const location = useLocation();
  const currentPath = location.pathname;

  const links = [
    { name: "Dashboard", path: "/" },
    { name: "Receipts", path: "/receipts" },
    { name: "Categories", path: "/categories" },
    { name: "Statistics", path: "/statistics" },
    { name: "Goals", path: "/goals" },
  ];

  return (
    <nav className="flex items-center gap-[2px]">
      {links.map((link) => {
        const isActive = currentPath === link.path;
        return (
          <Link
            key={link.name}
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
