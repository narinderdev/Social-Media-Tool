import { History, LayoutDashboard, LogOut } from "lucide-react";

import { APP_NAME } from "../constants";

function Sidebar({ route, user, onNavigate, onLogout }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-main">
        <div className="brand-block">
          <img className="brand-logo" src="/logo.png" alt="" />
          <div>
            <p className="eyebrow">{APP_NAME}</p>
            <h2>Admin</h2>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Dashboard">
          <button
            className={route === "dashboard" ? "nav-link active" : "nav-link"}
            type="button"
            onClick={() => onNavigate("dashboard")}
          >
            <LayoutDashboard size={18} />
            Posts
          </button>
          <button
            className={route === "posts" ? "nav-link active" : "nav-link"}
            type="button"
            onClick={() => onNavigate("posts")}
          >
            <History size={18} />
            History
          </button>
        </nav>
      </div>

      <div className="sidebar-footer">
        <div>
          <strong>{user.email}</strong>
          <span>{user.role}</span>
        </div>
        <button className="logout-button" type="button" onClick={onLogout}>
          <LogOut size={17} />
          Logout
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
