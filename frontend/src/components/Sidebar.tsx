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

  async function createWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = workspaceName.trim();
    if (!name) {
      setWorkspaceError("Nhập tên workspace.");
      return;
    }
    setCreating(true);
    setWorkspaceError("");
    try {
      await onCreateWorkspace(name);
      setWorkspaceName("");
      setWorkspaceFormOpen(false);
    } catch (reason) {
      setWorkspaceError(reason instanceof Error ? reason.message : "Không thể tạo workspace.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <aside className="sidebar">
      <div className="brand">LOCAL RAG</div>
      <div className="sidebar-section">
        <div className="sidebar-heading"><span>WORKSPACES</span><button className="text-button compact" onClick={() => setWorkspaceFormOpen(true)}>+ Tạo workspace</button></div>
        {workspaceFormOpen && <form className="inline-form" onSubmit={createWorkspace}>
          <input aria-label="Tên workspace" placeholder="Tên workspace" value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} autoFocus />
          <button className="primary-button small" disabled={creating}>{creating ? "…" : "Tạo"}</button>
          <button type="button" className="icon-button" aria-label="Hủy tạo workspace" onClick={() => setWorkspaceFormOpen(false)}>×</button>
          {workspaceError && <p className="form-error">{workspaceError}</p>}
        </form>}
        <nav className="workspace-list" aria-label="Workspaces">
          {workspaces.map((workspace) => <button key={workspace.id} className={workspace.id === activeWorkspaceId ? "nav-item active" : "nav-item"} onClick={() => onSelectWorkspace(workspace.id)}>{workspace.name}</button>)}
        </nav>
      </div>
      <div className="sidebar-section sessions-section">
        <div className="sidebar-heading"><span>HỘI THOẠI</span><button className="text-button compact" onClick={() => void onNewChat()} disabled={!activeWorkspaceId}>+ Chat mới</button></div>
        <nav className="session-list" aria-label="Hội thoại">
          {sessions.map((session) => <div className={session.id === activeSessionId ? "session-row active" : "session-row"} key={session.id}>
            <button className="session-title" onClick={() => void onSelectSession(session.id)}>{session.title}</button>
            <button className="icon-button session-action" aria-label={`Đổi tên ${session.title}`} onClick={() => void onRenameSession(session)}>✎</button>
            <button className="icon-button session-action" aria-label={`Xóa ${session.title}`} onClick={() => void onDeleteSession(session)}>×</button>
          </div>)}
        </nav>
      </div>
      <button className="logout-button" onClick={onLogout}>Đăng xuất</button>
    </aside>
  );
}
