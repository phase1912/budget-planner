import { Link } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { Moon, Sun } from "lucide-react";
import { useStores } from "@/stores/StoreContext";
import { Button } from "@/shared/components";
import { Navigation } from "./Navigation";

export const Header = observer(() => {
  const { themeStore } = useStores();

  return (
    <header className="flex-shrink-0 border-b border-border bg-surface px-8 py-4 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <Link
          to="/"
          className="text-xl font-bold bg-gradient-to-r from-primary to-primary-hover bg-clip-text text-transparent"
        >
          AI Budget Agent
        </Link>
        <Navigation />
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            themeStore.toggleTheme();
          }}
          aria-label="Toggle theme"
        >
          {themeStore.theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </Button>
      </div>
    </header>
  );
});
