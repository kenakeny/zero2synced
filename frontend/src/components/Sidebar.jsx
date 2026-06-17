import { PlusIcon } from "./Icons.jsx";

export default function Sidebar({ sessions, activeId, onSelect, onNew, user, onLogout, onDisconnectFivetran }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <img src="/logo.jpg" alt="Zero-to-Synced" className="brand-logo" />
        <div className="brand-name">
          Zero-to-Synced
          <small>pipeline agent</small>
        </div>
      </div>

      <button className="new-chat" onClick={onNew}>
        <PlusIcon /> New chat
      </button>

      <div className="rail-label">Sessions</div>
      <div className="session-list">
        {sessions.length === 0 ? (
          <div className="sidebar-empty">No sessions yet.</div>
        ) : (
          sessions.map((s) => (
            <button
              key={s.session_id}
              className={"session-item" + (s.session_id === activeId ? " active" : "")}
              onClick={() => onSelect(s.session_id)}
              title={s.title}
            >
              {s.title || "New chat"}
              <span className="ago">{timeAgo(s.last_active)}</span>
            </button>
          ))
        )}
      </div>

      {onDisconnectFivetran && (
        <div className="ft-status">
          <span className="ft-dot" />
          <span className="ft-label">Fivetran connected</span>
          <button className="ft-disconnect" onClick={onDisconnectFivetran}>
            Disconnect
          </button>
        </div>
      )}

      {user && (
        <div className="account">
          <div className="account-id">
            <span className="avatar">{user.email[0].toUpperCase()}</span>
            <span className="account-email" title={user.email}>
              {user.email}
            </span>
          </div>
          <button className="logout" onClick={onLogout} title="Sign out">
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}

function timeAgo(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  const s = Math.max(0, (Date.now() - then) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
