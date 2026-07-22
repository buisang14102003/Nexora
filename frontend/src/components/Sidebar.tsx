import { FormEvent, useEffect, useState } from "react";

import type { ChatSession, Workspace } from "../api/client";

type Props = {
  workspaces: Workspace[];
  activeWorkspaceId: string | null;
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectWorkspace: (workspaceId: string) => void;
  onCreateWorkspace: (name: string) => Promise<void>;
  onNewChat: () => Promise<unknown>;
  onSelectSession: (sessionId: string) => Promise<void>;
  onRenameSession: (session: ChatSession) => Promise<void>;
  onDeleteSession: (session: ChatSession) => Promise<void>;
  onLogout: () => void;
};

export function Sidebar({ workspaces, activeWorkspaceId, sessions, activeSessionId, onSelectWorkspace, onCreateWorkspace, onNewChat, onSelectSession, onRenameSession, onDeleteSession, onLogout }: Props) {
  const [workspaceFormOpen, setWorkspaceFormOpen] = useState(false);
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceError, setWorkspaceError] = useState("");
  const [creating, setCreating] = useState(false);
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

  function closeWorkspaceDialog() {
    setWorkspaceFormOpen(false);
    setWorkspaceName("");
    setWorkspaceError("");
  }

  async function createWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = workspaceName.trim();
    if (!name) {
      setWorkspaceError("Enter a workspace name.");
      return;
    }
    setCreating(true);
    setWorkspaceError("");
    try {
      await onCreateWorkspace(name);
      closeWorkspaceDialog();
    } catch (reason) {
      setWorkspaceError(reason instanceof Error ? reason.message : "We couldn't create the workspace.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="brand">Local RAG</div>
        <button className="new-chat-button" onClick={() => void onNewChat()} disabled={!activeWorkspaceId}>New chat</button>
      </div>
      <div className="sidebar-section workspace-section">
        <div className="sidebar-heading"><span>Workspaces</span><button className="text-button compact" onClick={() => setWorkspaceFormOpen(true)}>Create</button></div>
        <nav className="workspace-list" aria-label="Workspaces">
          {workspaces.map((workspace) => <button key={workspace.id} className={workspace.id === activeWorkspaceId ? "nav-item active" : "nav-item"} onClick={() => onSelectWorkspace(workspace.id)}>{workspace.name}</button>)}
        </nav>
      </div>
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
      {workspaceFormOpen && <dialog className="workspace-dialog" open onCancel={closeWorkspaceDialog} onClick={(event) => { if (event.target === event.currentTarget) closeWorkspaceDialog(); }}>
        <form className="workspace-dialog-card" onSubmit={createWorkspace}>
          <div className="dialog-heading"><h2>Create workspace</h2><button type="button" className="icon-button" aria-label="Close create workspace dialog" onClick={closeWorkspaceDialog}>×</button></div>
          <label>Workspace name<input placeholder="e.g. Product research" value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} autoFocus /></label>
          <p className="dialog-note">Workspaces keep documents and chats separate.</p>
          {workspaceError && <p className="form-error">{workspaceError}</p>}
          <div className="dialog-actions"><button type="button" className="text-button" onClick={closeWorkspaceDialog}>Cancel</button><button className="primary-button" disabled={creating}>{creating ? "Creating…" : "Create workspace"}</button></div>
          {workspaces.length > 0 && <div className="workspace-picker"><span>Or switch to an existing workspace</span>{workspaces.map((workspace) => <button type="button" key={workspace.id} onClick={() => { onSelectWorkspace(workspace.id); closeWorkspaceDialog(); }}>{workspace.name}</button>)}</div>}
        </form>
      </dialog>}
    </aside>
  );
}
