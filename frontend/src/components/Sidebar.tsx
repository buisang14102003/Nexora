import { FormEvent, useState } from "react";

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
      setWorkspaceName("");
      setWorkspaceFormOpen(false);
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
        {workspaceFormOpen && <form className="inline-form" onSubmit={createWorkspace}>
          <input aria-label="Workspace name" placeholder="Workspace name" value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} autoFocus />
          <button className="primary-button small" disabled={creating}>{creating ? "…" : "Create"}</button>
          <button type="button" className="icon-button" aria-label="Cancel workspace creation" onClick={() => setWorkspaceFormOpen(false)}>Cancel</button>
          {workspaceError && <p className="form-error">{workspaceError}</p>}
        </form>}
        <nav className="workspace-list" aria-label="Workspaces">
          {workspaces.map((workspace) => <button key={workspace.id} className={workspace.id === activeWorkspaceId ? "nav-item active" : "nav-item"} onClick={() => onSelectWorkspace(workspace.id)}>{workspace.name}</button>)}
        </nav>
      </div>
      <div className="sidebar-section sessions-section">
        <div className="sidebar-heading"><span>Recent</span></div>
        <nav className="session-list" aria-label="Chats">
          {sessions.map((session) => <div className={session.id === activeSessionId ? "session-row active" : "session-row"} key={session.id}>
            <button className="session-title" onClick={() => void onSelectSession(session.id)}>{session.title}</button>
            <button className="icon-button session-action" aria-label={`Rename ${session.title}`} onClick={() => void onRenameSession(session)}>Rename</button>
            <button className="icon-button session-action" aria-label={`Delete ${session.title}`} onClick={() => void onDeleteSession(session)}>Delete</button>
          </div>)}
        </nav>
      </div>
      <div className="profile-menu-wrap">
        {profileMenuOpen && <div className="profile-menu">
          <a href="http://127.0.0.1:3100" target="_blank" rel="noreferrer">Xem log Langfuse</a>
          <button onClick={onLogout}>Sign out</button>
        </div>}
        <button className="account-button" aria-label="Open account menu" aria-expanded={profileMenuOpen} onClick={() => setProfileMenuOpen((open) => !open)}><span>R</span><span>Account</span></button>
      </div>
    </aside>
  );
}
