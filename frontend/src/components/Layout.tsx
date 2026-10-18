import { NavLink, Outlet } from "react-router-dom";
import { useLiveUpdates } from "../api/useLiveUpdates";
import { useAuth } from "../auth/AuthContext";

const AUTHOR_NAV = [
  { to: "/books", label: "My Books" },
  { to: "/tickets", label: "My Tickets" },
  { to: "/tickets/new", label: "Get Help" },
];

const ADMIN_NAV = [
  { to: "/admin/tickets", label: "Ticket Queue" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const live = useLiveUpdates();
  const nav = user?.role === "admin" ? ADMIN_NAV : AUTHOR_NAV;

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <img src="/favicon.svg" alt="" width={26} height={26} />
            <span>BookLeaf</span>
            <span className="brand-sub">{user?.role === "admin" ? "Support Desk" : "Author Portal"}</span>
          </div>
          <nav className="nav">
            {nav.map((item) => (
              <NavLink key={item.to} to={item.to} end>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="topbar-right">
            <span className={`live live-${live}`} title={live === "live" ? "Updates arrive in real time" : "Reconnecting…"}>
              <span className="live-dot" />
              {live === "live" ? "Live" : "Reconnecting"}
            </span>
            <span className="user-name">{user?.name}</span>
            <button className="btn btn-ghost btn-sm" onClick={logout}>
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
