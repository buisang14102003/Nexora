import { useEffect, useState } from "react";

import type { ChatSession, Workspace } from "../api/client";

type Props = {
  pinned: Workspace[];
  activeWorkspaceId: string | null;
  managerActive: boolean;
  sessions: ChatSession[];
  activeSessionId: string | null;
  onOpenManager: () => void;
  onSelectWorkspace: (workspaceId: string) => void;
  onNewChat: () => Promise<unknown>;
  onSelectSession: (sessionId: string) => Promise<void>;
  onRenameSession: (session: ChatSession) => Promise<void>;
  onDeleteSession: (session: ChatSession) => Promise<void>;
  onLogout: () => void;
};

export function Sidebar({ pinned, activeWorkspaceId, managerActive, sessions, activeSessionId, onOpenManager, onSelectWorkspace, onNewChat, onSelectSession, onRenameSession, onDeleteSession, onLogout }: Props) {
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [sessionMenuId, setSessionMenuId] = useState<string | null>(null);
  const [theme, setTheme] = useState<"light" | "dark" | "system">((localStorage.getItem("theme") as "light" | "dark" | "system") || "system");

  useEffect(() => {
    const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    function closeMenus(event: PointerEvent) {
      if (!(event.target instanceof Element)) return;
      if (!event.target.closest(".profile-menu-wrap")) setProfileMenuOpen(false);
      if (!event.target.closest(".session-menu-wrap")) setSessionMenuId(null);
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setProfileMenuOpen(false);
        setSessionMenuId(null);
      }
    }
    document.addEventListener("pointerdown", closeMenus);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeMenus);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="brand">Local RAG</div>
        <button className="new-chat-button" onClick={() => void onNewChat()} disabled={!activeWorkspaceId}>New chat</button>
      </div>
      <button className={managerActive ? "workspace-manager-link active" : "workspace-manager-link"} onClick={onOpenManager}>
        <span className="workspace-manager-link-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M3.75 6.75h6l1.5 2.25h9v8.25a1.5 1.5 0 0 1-1.5 1.5h-15a1.5 1.5 0 0 1-1.5-1.5v-9a1.5 1.5 0 0 1 1.5-1.5Z" /></svg></span>
        <span>Workspaces</span>
      </button>
      {pinned.length > 0 && <div className="sidebar-section workspace-section">
        <div className="sidebar-heading"><span>Pinned</span></div>
        <nav className="workspace-list" aria-label="Pinned workspaces">
          {pinned.map((workspace) => <button key={workspace.id} className={!managerActive && workspace.id === activeWorkspaceId ? "nav-item active" : "nav-item"} onClick={() => onSelectWorkspace(workspace.id)}>{workspace.name}</button>)}
        </nav>
      </div>}
      <div className="sidebar-section sessions-section">
        <div className="sidebar-heading"><span>Recent</span></div>
        <nav className="session-list" aria-label="Chats">
          {sessions.map((session) => <div className={session.id === activeSessionId ? "session-row active" : "session-row"} key={session.id}>
            <button className="session-title" onClick={() => void onSelectSession(session.id)}>{session.title}</button>
            <div className="session-menu-wrap">
              <button className="icon-button session-menu-trigger" aria-label={`Open actions for ${session.title}`} aria-expanded={sessionMenuId === session.id} onClick={() => setSessionMenuId((open) => open === session.id ? null : session.id)}>•••</button>
              {sessionMenuId === session.id && <div className="session-menu" role="menu">
                <button role="menuitem" onClick={() => { setSessionMenuId(null); void onRenameSession(session); }}>Rename</button>
                <button className="danger" role="menuitem" onClick={() => { setSessionMenuId(null); void onDeleteSession(session); }}>Delete</button>
              </div>}
            </div>
          </div>)}
        </nav>
      </div>
      <div className="profile-menu-wrap">
        {profileMenuOpen && <div className="profile-menu">
          <div className="profile-summary"><span className="profile-avatar">R</span><span><strong>Local RAG</strong><small>Local workspace</small></span><b>›</b></div>
          <div className="profile-divider" />
          <div className="theme-control"><span>Theme</span><div>{(["light", "dark", "system"] as const).map((mode) => <button key={mode} className={theme === mode ? "theme-option active" : "theme-option"} onClick={() => setTheme(mode)}>{mode}</button>)}</div></div>
          <a href="http://127.0.0.1:3100" target="_blank" rel="noreferrer">Observability</a>
          <button onClick={onLogout}>Log out</button>
        </div>}
        <button className="account-button" aria-label="Open settings menu" aria-expanded={profileMenuOpen} onClick={() => setProfileMenuOpen((open) => !open)}><span>R</span><span>Settings</span></button>
      </div>
    </aside>
  );
}
