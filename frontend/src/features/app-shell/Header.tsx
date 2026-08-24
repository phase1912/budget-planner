import { Link, useNavigate } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { Moon, Sun, LogOut, Upload, Settings } from "lucide-react";
import { useStores } from "@/stores/StoreContext";
import { Button } from "@/shared/components";
import { Navigation } from "./Navigation";
import { useState, useRef, useEffect } from "react";

export const Header = observer(() => {
  const { themeStore, authStore } = useStores();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const handleLogout = async () => {
    await authStore.logout();
    setMenuOpen(false);
    void navigate("/login");
  };

  const getInitials = () => {
    if (!authStore.user) return "?";
    const first = authStore.user.first_name.charAt(0);
    const last = authStore.user.last_name.charAt(0);
    return (first + last).toUpperCase() || "?";
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <header className="flex-shrink-0 border-b border-border bg-surface px-8 py-3.5 flex items-center justify-between">
      <div className="flex items-center gap-7">
        <Link
          to="/"
          className="text-[20px] font-bold bg-gradient-to-r from-primary to-primary-hover bg-clip-text text-transparent"
        >
          Budget Agent
        </Link>
        {authStore.isAuthenticated && <Navigation />}
      </div>
      <div className="flex items-center gap-2.5">
        {authStore.isAuthenticated ? (
          <>
            <Link to="/upload" className="contents">
              <Button size="compact" className="hidden sm:flex">
                <Upload size={16} className="mr-2" />
                Upload
              </Button>
            </Link>
            <Button
              variant="ghost"
              size="compact"
              onClick={() => {
                themeStore.toggleTheme();
              }}
              aria-label="Toggle theme"
              className="px-2"
            >
              {themeStore.theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </Button>
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => {
                  setMenuOpen(!menuOpen);
                }}
                className={`inline-flex items-center justify-center border rounded-full bg-surface p-[5px] cursor-pointer transition-colors ${menuOpen ? "border-primary" : "border-border"}`}
                aria-label="Account menu"
              >
                <span className="inline-flex items-center justify-center w-[30px] h-[30px] rounded-full bg-primary/10 text-primary text-[13px] font-semibold">
                  {getInitials()}
                </span>
              </button>

              {menuOpen && (
                <div className="absolute right-0 top-[calc(100%+8px)] z-20 border border-border rounded-xl bg-background shadow-lg p-1.5 flex flex-col gap-[1px] min-w-[200px]">
                  <div className="px-3 py-2 border-b border-border mb-1">
                    <p className="text-sm font-semibold">{authStore.user?.email}</p>
                  </div>
                  <Link
                    to="/profile"
                    onClick={() => {
                      setMenuOpen(false);
                    }}
                    className="flex items-center justify-between gap-2.5 rounded-lg px-3 py-2 text-[14px] text-foreground hover:bg-surface-hover transition-colors"
                  >
                    Preferences
                    <Settings size={16} className="text-muted-foreground" />
                  </Link>
                  <button
                    onClick={() => {
                      void handleLogout();
                    }}
                    className="flex items-center justify-between gap-2.5 rounded-lg px-3 py-2 text-[14px] text-error hover:bg-tone-error-bg transition-colors"
                  >
                    Log out
                    <LogOut size={16} />
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <>
            <Button
              variant="ghost"
              size="compact"
              onClick={() => {
                themeStore.toggleTheme();
              }}
              aria-label="Toggle theme"
              className="px-2"
            >
              {themeStore.theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </Button>
            <Link to="/login" className="contents">
              <Button variant="ghost" size="compact">
                Sign in
              </Button>
            </Link>
            <Link to="/register" className="contents">
              <Button size="compact">Create an account</Button>
            </Link>
          </>
        )}
      </div>
    </header>
  );
});
