import { useState, useEffect, useRef } from "react";
import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast"; 
import {
  LayoutDashboard,
  Mail,
  CheckSquare,
  Briefcase,
  CalendarDays,
  Search,
  LogOut,
  Menu,
  X,
  ChevronDown,
  Zap,
  RefreshCw,
} from "lucide-react";
import { useAuthStore } from "../store/authStore";
import { apiClient } from "../services/api/client";
import { syncEmails } from "../services/api/sync";

/* ── Nav config ─────────────────────────────── */
interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  end?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard",  path: "/",           icon: <LayoutDashboard size={15} strokeWidth={1.8} />, end: true },
  { label: "Emails",     path: "/emails",     icon: <Mail            size={15} strokeWidth={1.8} /> },
  { label: "Tasks",      path: "/tasks",      icon: <CheckSquare     size={15} strokeWidth={1.8} /> },
  { label: "Jobs",       path: "/jobs",       icon: <Briefcase       size={15} strokeWidth={1.8} /> },
  { label: "Interviews", path: "/interviews", icon: <CalendarDays    size={15} strokeWidth={1.8} /> },
  { label: "Search",     path: "/search",     icon: <Search          size={15} strokeWidth={1.8} /> },
];

/* ── Component ──────────────────────────────── */
export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const userMenuRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  // Close mobile nav on route change
  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  // Close user menu on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Prevent body scroll when mobile nav is open
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [mobileOpen]);

  async function handleLogout() {
    setUserMenuOpen(false);
    await apiClient.post("/auth/logout");
    clearAuth();
    navigate("/login");
  }

  async function handleSyncEmails() {
    if (isSyncing) return;
    setIsSyncing(true);
    const toastId = toast.loading("Syncing emails...");
    try {
      await syncEmails();
      toast.success("Emails synced successfully!", { id: toastId });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["emails"] });
    } catch (error) {
      toast.error("Sync failed. Please try again.", { id: toastId });
      console.error("Sync error:", error);
    } finally {
      setIsSyncing(false);
    }
  }
  const initials = user?.name
    ? user.name.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase()
    : user?.email?.[0]?.toUpperCase() ?? "U";

  const displayName = user?.name ?? user?.email ?? "User";
  const displayEmail = user?.email ?? "";

  /* ── Sidebar content (shared desktop/mobile) ── */
  const sidebarContent = (
    <div className="al-sidebar-inner">
      {/* Logo */}
      <div className="al-logo">
        <div className="al-logo-mark" aria-hidden="true">
          <Zap size={13} strokeWidth={2.5} />
        </div>
        <span className="al-logo-text">Mail Intel</span>
      </div>

      {/* Nav */}
      <nav className="al-nav" aria-label="Main navigation">
        <div className="al-nav-section-label">Workspace</div>
        <ul className="al-nav-list" role="list">
          {NAV_ITEMS.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                end={item.end}
                className={({ isActive }) =>
                  `al-nav-item ${isActive ? "al-nav-item--active" : ""}`
                }
                aria-current={undefined}
              >
                <span className="al-nav-icon" aria-hidden="true">
                  {item.icon}
                </span>
                <span className="al-nav-label">{item.label}</span>
                <span className="al-nav-active-pip" aria-hidden="true" />
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Spacer */}
      <div className="al-sidebar-spacer" />

      {/* User area */}
      <div className="al-user-area" ref={userMenuRef}>
        <button
          className="al-user-trigger"
          onClick={() => setUserMenuOpen((v) => !v)}
          aria-haspopup="menu"
          aria-expanded={userMenuOpen}
          aria-label="User menu"
        >
          <div className="al-avatar" aria-hidden="true">{initials}</div>
          <div className="al-user-info">
            <span className="al-user-name">{displayName}</span>
            {displayEmail && <span className="al-user-email">{displayEmail}</span>}
          </div>
          <ChevronDown
            size={13}
            strokeWidth={2}
            className={`al-user-chevron ${userMenuOpen ? "al-user-chevron--open" : ""}`}
            aria-hidden="true"
          />
        </button>

        {userMenuOpen && (
          <div className="al-user-menu" role="menu" aria-label="User options">
            <div className="al-user-menu-header">
              <span className="al-user-menu-name">{displayName}</span>
              {displayEmail && (
                <span className="al-user-menu-email">{displayEmail}</span>
              )}
            </div>
            <div className="al-user-menu-divider" role="separator" />
            <button
              className="al-user-menu-item al-user-menu-item--danger"
              role="menuitem"
              onClick={handleLogout}
            >
              <LogOut size={13} strokeWidth={2} aria-hidden="true" />
              Sign out
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      <style>{CSS}</style>
      <div className="al-root">

        {/* ── Desktop sidebar ── */}
        <aside className="al-sidebar" aria-label="Sidebar">
          {sidebarContent}
        </aside>

        {/* ── Mobile backdrop ── */}
        {mobileOpen && (
          <div
            className="al-backdrop"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* ── Mobile sidebar ── */}
        <aside
          className={`al-sidebar al-sidebar--mobile ${mobileOpen ? "al-sidebar--open" : ""}`}
          aria-label="Mobile navigation"
          aria-hidden={!mobileOpen}
        >
          <button
            className="al-mobile-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <X size={16} strokeWidth={2} />
          </button>
          {sidebarContent}
        </aside>

        {/* Main area */}
        <div className="al-main">
          <header className="al-topbar" aria-label="Top bar">
            <button
              className="al-menu-trigger"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
              aria-expanded={mobileOpen}
            >
              <Menu size={18} strokeWidth={2} />
            </button>
            <div className="al-topbar-logo">
              <div className="al-logo-mark al-logo-mark--sm" aria-hidden="true">
                <Zap size={11} strokeWidth={2.5} />
              </div>
              <span className="al-logo-text al-logo-text--sm">Mail Intel</span>
            </div>

            {/* Sync button - added here */}
            <button
              className="al-sync-btn"
              onClick={handleSyncEmails}
              disabled={isSyncing}
              aria-label="Sync emails"
            >
              {isSyncing ? (
                <RefreshCw size={14} strokeWidth={2} className="animate-spin" />
              ) : (
                <RefreshCw size={14} strokeWidth={2} />
              )}
              <span>Sync emails</span>
            </button>
          </header>

          <main className="al-content" id="main-content" tabIndex={-1}>
            <Outlet />
          </main>
        </div>
      </div>
    </>
  );
}

/* ── Styles ─────────────────────────────────── */
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');

/* ─ Root layout ─ */
.al-root {
  display: flex;
  min-height: 100dvh;
  background: #0b0b0f;
  font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* ─ Sidebar ─ */
.al-sidebar {
  width: 220px;
  flex-shrink: 0;
  height: 100dvh;
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  background: #0f0f14;
  border-right: 1px solid rgba(255,255,255,0.055);
  z-index: 40;
  overflow: hidden;
}

.al-sidebar--mobile {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 260px;
  transform: translateX(-100%);
  transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 60;
  box-shadow: 4px 0 32px rgba(0,0,0,0.5);
  display: none;
}

.al-sidebar--mobile.al-sidebar--open {
  transform: translateX(0);
}

.al-sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
}

/* ─ Logo ─ */
.al-logo {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 20px 16px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  flex-shrink: 0;
}

.al-logo-mark {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 0 0 1px rgba(124,58,237,0.35), 0 2px 8px rgba(124,58,237,0.25);
}

.al-logo-mark--sm {
  width: 22px;
  height: 22px;
  border-radius: 6px;
}

.al-logo-text {
  font-size: 14.5px;
  font-weight: 600;
  letter-spacing: -0.025em;
  color: #f0ecff;
}

.al-logo-text--sm {
  font-size: 14px;
}

/* ─ Nav ─ */
.al-nav {
  flex: 1;
  padding: 16px 8px 8px;
  overflow-y: auto;
  overflow-x: hidden;
}

.al-nav::-webkit-scrollbar { width: 0; }

.al-nav-section-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #3d3955;
  padding: 0 8px;
  margin-bottom: 6px;
}

.al-nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

/* ─ Nav item ─ */
.al-nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 7px 9px 7px 10px;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 450;
  letter-spacing: -0.01em;
  color: #6b6585;
  text-decoration: none;
  cursor: pointer;
  transition:
    background 0.13s cubic-bezier(0.16,1,0.3,1),
    color 0.13s cubic-bezier(0.16,1,0.3,1);
  border: 1px solid transparent;
  user-select: none;
}

.al-nav-item:hover {
  background: rgba(255,255,255,0.04);
  color: #ccc6e8;
}

.al-nav-item:hover .al-nav-icon { opacity: 0.9; }

.al-nav-item--active {
  background: rgba(124,58,237,0.12);
  color: #c4b5fd;
  border-color: rgba(124,58,237,0.18);
  font-weight: 500;
}

.al-nav-item--active .al-nav-icon {
  color: #a78bfa;
  opacity: 1;
}

.al-nav-item--active:hover {
  background: rgba(124,58,237,0.15);
  color: #d4c8ff;
}

/* Active left-edge indicator */
.al-nav-active-pip {
  display: none;
  position: absolute;
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 16px;
  border-radius: 0 2px 2px 0;
  background: #7c3aed;
  box-shadow: 0 0 8px rgba(124,58,237,0.6);
}

.al-nav-item--active .al-nav-active-pip { display: block; }

.al-nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  opacity: 0.5;
  transition: opacity 0.13s, color 0.13s;
  color: inherit;
  width: 16px;
  height: 16px;
}

.al-nav-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ─ Spacer ─ */
.al-sidebar-spacer { flex: 1; min-height: 16px; }

/* ─ User area ─ */
.al-user-area {
  padding: 8px;
  border-top: 1px solid rgba(255,255,255,0.05);
  flex-shrink: 0;
  position: relative;
}

.al-user-trigger {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 8px 8px 8px 9px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition:
    background 0.13s,
    border-color 0.13s;
}

.al-user-trigger:hover {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.06);
}

.al-user-trigger:focus-visible {
  outline: 2px solid rgba(124,58,237,0.6);
  outline-offset: 1px;
}

/* ─ Avatar ─ */
.al-avatar {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: linear-gradient(135deg, #4c1d95 0%, #312e81 100%);
  border: 1px solid rgba(124,58,237,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: #c4b5fd;
  flex-shrink: 0;
}

.al-user-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.al-user-name {
  font-size: 12.5px;
  font-weight: 500;
  color: #b8b0d4;
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.al-user-email {
  font-size: 11px;
  color: #433e60;
  letter-spacing: -0.005em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.al-user-chevron {
  color: #3d3960;
  flex-shrink: 0;
  transition: transform 0.18s cubic-bezier(0.16,1,0.3,1), color 0.13s;
}

.al-user-chevron--open {
  transform: rotate(180deg);
  color: #7c3aed;
}

/* ─ User menu dropdown ─ */
.al-user-menu {
  position: absolute;
  bottom: calc(100% - 6px);
  left: 8px;
  right: 8px;
  background: #17151f;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  box-shadow:
    0 -8px 32px rgba(0,0,0,0.6),
    0 0 0 1px rgba(255,255,255,0.03) inset;
  padding: 6px;
  z-index: 10;
  animation: al-menu-in 0.16s cubic-bezier(0.16,1,0.3,1);
}

@keyframes al-menu-in {
  from { opacity: 0; transform: translateY(4px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.al-user-menu-header {
  padding: 8px 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.al-user-menu-name {
  font-size: 12.5px;
  font-weight: 500;
  color: #c8c0e4;
  letter-spacing: -0.01em;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.al-user-menu-email {
  font-size: 11px;
  color: #4a4568;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.al-user-menu-divider {
  height: 1px;
  background: rgba(255,255,255,0.06);
  margin: 2px 0 4px;
}

.al-user-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 8px;
  border-radius: 6px;
  background: transparent;
  border: none;
  font-family: inherit;
  font-size: 13px;
  font-weight: 450;
  letter-spacing: -0.01em;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
  text-align: left;
  color: #6b6585;
}

.al-user-menu-item:hover {
  background: rgba(255,255,255,0.04);
  color: #c4b5fd;
}

.al-user-menu-item--danger:hover {
  background: rgba(244,63,94,0.1);
  color: #fda4af;
}

.al-user-menu-item:focus-visible {
  outline: 2px solid rgba(124,58,237,0.5);
  outline-offset: 1px;
}

/* ─ Main area ─ */
.al-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #0b0b0f;
}

/* ─ Mobile topbar (hidden on desktop) ─ */
.al-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 52px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255,255,255,0.055);
  background: #0f0f14;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 30;
}

.al-topbar-logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.al-menu-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid rgba(255,255,255,0.08);
  color: #6b6585;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.13s, color 0.13s, border-color 0.13s;
}

/* Sync button */
.al-sync-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(124,58,237,0.1);
  border: 1px solid rgba(124,58,237,0.25);
  color: #c4b5fd;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.13s ease;
  white-space: nowrap;
}

.al-sync-btn:hover:not(:disabled) {
  background: rgba(124,58,237,0.2);
  border-color: rgba(124,58,237,0.5);
  color: #ddd6fe;
}

.al-sync-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.animate-spin {
  animation: spin 0.8s linear infinite;
}

.al-menu-trigger:hover {
  background: rgba(255,255,255,0.05);
  color: #c4b5fd;
  border-color: rgba(124,58,237,0.25);
}

.al-menu-trigger:focus-visible {
  outline: 2px solid rgba(124,58,237,0.6);
  outline-offset: 1px;
}

/* ─ Mobile close btn ─ */
.al-mobile-close {
  display: none;
  position: absolute;
  top: 16px;
  right: 14px;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: #6b6585;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  transition: background 0.12s, color 0.12s;
  z-index: 1;
}

.al-mobile-close:hover {
  background: rgba(255,255,255,0.07);
  color: #c4b5fd;
}

/* ─ Page content ─ */
.al-content {
  flex: 1;
  padding: 32px 36px;
  overflow-y: auto;
  outline: none;
}

/* ─ Backdrop ─ */
.al-backdrop {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.55);
  backdrop-filter: blur(3px);
  z-index: 55;
  animation: al-fade-in 0.2s ease;
}

@keyframes al-fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

/* ─ Responsive ─ */
@media (max-width: 768px) {
  .al-sidebar:not(.al-sidebar--mobile) {
    display: none;
  }

  .al-sidebar--mobile {
    display: flex;
  }

  .al-topbar {
    display: flex;
  }

  .al-backdrop {
    display: block;
  }

  .al-mobile-close {
    display: flex;
  }

  .al-content {
    padding: 20px 16px 32px;
  }
}

@media (min-width: 769px) {
  .al-sidebar--mobile {
    display: none !important;
  }

  .al-backdrop {
    display: none !important;
  }
}

@media (max-width: 480px) {
  .al-content {
    padding: 16px 12px 28px;
  }
}

@media (min-width: 1600px) {
  .al-content {
    padding: 40px 48px;
  }
}
`;
