import { Link, useLocation, useNavigate } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { ArrowLeft, Moon, Sun, LogOut, Upload, Settings } from "lucide-react";
import { useStores } from "@/stores/StoreContext";
import { Button } from "@/shared/components";
import { Navigation } from "./Navigation";
import { useState, useRef, useEffect } from "react";

export const Header = observer(() => {
  const { themeStore, authStore } = useStores();
  const navigate = useNavigate();
  const { pathname } = useLocation();
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

  // On a phone the upload flow is a focused task: a way back and its name, no more
  // (docs/design/screens/upload-mobile.html).
  const uploading = authStore.isAuthenticated && pathname.startsWith("/upload");

  return (
    <header className="flex-shrink-0 border-b border-border bg-surface px-4 py-3 md:px-8 md:py-3.5 flex items-center justify-between">
      {uploading && (
        <div className="flex items-center gap-2 md:hidden">
          <Link
            to="/"
            aria-label="Back"
            className="-ml-2 inline-flex h-11 w-11 items-center justify-center rounded-chip text-foreground hover:bg-muted"
          >
            <ArrowLeft size={20} aria-hidden="true" />
          </Link>
          <h1 className="m-0 text-[17px] font-bold">New receipt</h1>
        </div>
      )}
      <div className={`items-center gap-7 ${uploading ? "hidden md:flex" : "flex"}`}>
        <Link
          to="/"
          className="text-[17px] md:text-[20px] font-bold bg-gradient-to-r from-primary to-primary-hover bg-clip-text text-transparent"
        >
          Budget Agent
        </Link>
        {/* A phone navigates from the bottom bar instead (BottomNavigation). */}
        {authStore.isAuthenticated && (
          <div className="hidden md:block">
            <Navigation />
          </div>
        )}
      </div>
      <div className={`items-center gap-2.5 ${uploading ? "hidden md:flex" : "flex"}`}>
        {authStore.isAuthenticated ? (
          <>
            {/* A phone uploads from the bottom bar's centre button. */}
            <Link to="/upload" className="hidden md:contents">
              <Button size="compact">
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
              className="h-11 w-11 justify-center px-2 md:h-auto md:w-auto"
            >
              {themeStore.theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </Button>
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => {
                  setMenuOpen(!menuOpen);
                }}
                className={`inline-flex h-11 w-11 items-center justify-center border rounded-full bg-surface p-[5px] cursor-pointer md:h-auto md:w-auto transition-colors ${menuOpen ? "border-primary" : "border-border"}`}
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
              className="h-11 w-11 justify-center px-2 md:h-auto md:w-auto"
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
