import { FormEvent, useEffect, useMemo, useState } from "react";

import type { Workspace, WorkspaceStatus, WorkspaceUpdate } from "../api/client";
import { filterWorkspaces } from "../workspaces/state";

type Props = {
  activeWorkspaces: Workspace[];
  archivedWorkspaces: Workspace[];
  loading: boolean;
  error: string;
  onLoadArchived: () => Promise<void>;
  onCreate: (name: string) => Promise<void>;
  onOpen: (workspaceId: string) => void;
  onUpdate: (workspaceId: string, update: WorkspaceUpdate) => Promise<void>;
  onArchive: (workspaceId: string) => Promise<void>;
  onRestore: (workspaceId: string) => Promise<void>;
};

type DialogState =
  | { type: "create" }
  | { type: "rename"; workspace: Workspace }
  | { type: "archive"; workspace: Workspace }
  | null;

const modifiedDate = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
});

function apiMessage(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback;
}

export function WorkspaceManager({ activeWorkspaces, archivedWorkspaces, loading, error, onLoadArchived, onCreate, onOpen, onUpdate, onArchive, onRestore }: Props) {
  const [status, setStatus] = useState<WorkspaceStatus>("active");
  const [query, setQuery] = useState("");
  const [menuId, setMenuId] = useState<string | null>(null);
  const [dialog, setDialog] = useState<DialogState>(null);
  const [name, setName] = useState("");
  const [formError, setFormError] = useState("");
  const [pendingId, setPendingId] = useState<string | null>(null);

  const visibleWorkspaces = useMemo(
    () => filterWorkspaces(status === "active" ? activeWorkspaces : archivedWorkspaces, query),
    [activeWorkspaces, archivedWorkspaces, query, status],
  );

  useEffect(() => {
    function closeMenu(event: PointerEvent) {
      if (event.target instanceof Element && !event.target.closest(".workspace-menu-wrap")) setMenuId(null);
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuId(null);
    }
    document.addEventListener("pointerdown", closeMenu);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeMenu);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  function closeDialog() {
    if (pendingId) return;
    setDialog(null);
    setName("");
    setFormError("");
  }

  function openNameDialog(type: "create" | "rename", workspace?: Workspace) {
    setMenuId(null);
    setName(workspace?.name ?? "");
    setFormError("");
    if (type === "create") setDialog({ type });
    else if (workspace) setDialog({ type, workspace });
  }

  async function selectArchivedTab() {
    setStatus("archived");
    setMenuId(null);
    setFormError("");
    await onLoadArchived();
  }

  async function submitName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setFormError("Enter a workspace name.");
      return;
    }
    const targetId = dialog?.type === "rename" ? dialog.workspace.id : "create";
    setPendingId(targetId);
    setFormError("");
    try {
      if (dialog?.type === "rename") await onUpdate(dialog.workspace.id, { name: trimmedName });
      else await onCreate(trimmedName);
      setDialog(null);
      setName("");
    } catch (reason) {
      setFormError(apiMessage(reason, `We couldn't ${dialog?.type === "rename" ? "rename" : "create"} the workspace.`));
    } finally {
      setPendingId(null);
    }
  }

  async function runRowAction(workspace: Workspace, action: "pin" | "restore") {
    setMenuId(null);
    setPendingId(workspace.id);
    setFormError("");
    try {
      if (action === "pin") await onUpdate(workspace.id, { is_pinned: !workspace.is_pinned });
      else await onRestore(workspace.id);
    } catch (reason) {
      setFormError(apiMessage(reason, `We couldn't ${action === "pin" ? "update" : "restore"} the workspace.`));
    } finally {
      setPendingId(null);
    }
  }

  async function confirmArchive() {
    if (dialog?.type !== "archive") return;
    setPendingId(dialog.workspace.id);
    setFormError("");
    try {
      await onArchive(dialog.workspace.id);
      setDialog(null);
    } catch (reason) {
      setFormError(apiMessage(reason, "We couldn't archive the workspace."));
    } finally {
      setPendingId(null);
    }
  }

  function renderWorkspaceRow(workspace: Workspace) {
    const archived = status === "archived";
    const pending = pendingId === workspace.id;
    const rowContent = <>
      <span className="workspace-folder-icon">
        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3.75 6.75h6l1.5 2.25h9v8.25a1.5 1.5 0 0 1-1.5 1.5h-15a1.5 1.5 0 0 1-1.5-1.5v-9a1.5 1.5 0 0 1 1.5-1.5Z" /></svg>
      </span>
      <span className="workspace-row-copy">
        <span className="workspace-row-name">{workspace.name}</span>
        <span className="workspace-mobile-modified">Modified {modifiedDate.format(new Date(workspace.updated_at))}</span>
      </span>
      {workspace.is_pinned && <svg className="workspace-pin-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="m8 4 8 0-1 5 3 3v2h-5v6l-1 1-1-1v-6H6v-2l3-3-1-5Z" /></svg>}
    </>;

    return <article className="workspace-row" key={workspace.id} aria-busy={pending || undefined}>
      {archived
        ? <div className="workspace-row-main workspace-row-static">{rowContent}</div>
        : <button className="workspace-row-main" onClick={() => onOpen(workspace.id)} disabled={pending}>{rowContent}</button>}
      <time className="workspace-modified" dateTime={workspace.updated_at}>{modifiedDate.format(new Date(workspace.updated_at))}</time>
      <div className="workspace-menu-wrap">
        <button className="workspace-menu-trigger" aria-label={`Open actions for ${workspace.name}`} aria-expanded={menuId === workspace.id} disabled={pending} onClick={() => setMenuId((open) => open === workspace.id ? null : workspace.id)}>
          <svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="19" cy="12" r="1.5" /></svg>
        </button>
        {menuId === workspace.id && <div className="workspace-menu" role="menu">
          {archived
            ? <button role="menuitem" onClick={() => void runRowAction(workspace, "restore")}>Restore</button>
            : <>
              <button role="menuitem" onClick={() => { setMenuId(null); onOpen(workspace.id); }}>Open</button>
              <button role="menuitem" onClick={() => void runRowAction(workspace, "pin")}>{workspace.is_pinned ? "Unpin workspace" : "Pin workspace"}</button>
              <button role="menuitem" onClick={() => openNameDialog("rename", workspace)}>Rename</button>
              <button className="danger" role="menuitem" onClick={() => { setMenuId(null); setFormError(""); setDialog({ type: "archive", workspace }); }}>Archive</button>
            </>}
        </div>}
      </div>
    </article>;
  }

  function renderEmptyState() {
    if (loading) return <div className="workspace-skeleton" aria-label="Loading workspaces">
      {[0, 1, 2].map((row) => <span key={row}><i /><i /></span>)}
    </div>;
    if (query) return <div className="workspace-empty">
      <svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m15.5 15.5 4 4" /></svg>
      <h2>No matching workspaces</h2>
      <p>No workspace matches “{query}”.</p>
      <button className="text-button" onClick={() => setQuery("")}>Clear search</button>
    </div>;
    if (status === "archived") return <div className="workspace-empty">
      <h2>No archived workspaces</h2>
      <p>Workspaces you archive will appear here.</p>
    </div>;
    return <div className="workspace-empty">
      <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3.75 6.75h6l1.5 2.25h9v8.25a1.5 1.5 0 0 1-1.5 1.5h-15a1.5 1.5 0 0 1-1.5-1.5v-9a1.5 1.5 0 0 1 1.5-1.5Z" /></svg>
      <h2>Create your first workspace</h2>
      <p>Workspaces keep documents and chats separate.</p>
      <button className="workspace-empty-action" onClick={() => openNameDialog("create")}>New workspace</button>
    </div>;
  }

  function renderDialog() {
    if (!dialog) return null;
    if (dialog.type === "archive") {
      const pending = pendingId === dialog.workspace.id;
      return <dialog className="workspace-dialog" open aria-labelledby="archive-workspace-title" onCancel={closeDialog} onClick={(event) => { if (event.target === event.currentTarget) closeDialog(); }}>
        <div className="workspace-dialog-card workspace-confirmation">
          <div className="dialog-heading"><h2 id="archive-workspace-title">Archive workspace</h2><button type="button" className="icon-button" aria-label="Close archive workspace dialog" disabled={pending} onClick={closeDialog}>×</button></div>
          <p><strong>“{dialog.workspace.name}”</strong> and its documents and chats remain saved, but they will be unavailable until you restore the workspace.</p>
          {formError && <p className="form-error" role="alert">{formError}</p>}
          <div className="dialog-actions"><button type="button" className="text-button" disabled={pending} onClick={closeDialog}>Cancel</button><button type="button" className="workspace-danger-button" disabled={pending} onClick={() => void confirmArchive()}>{pending ? "Archiving…" : "Archive"}</button></div>
        </div>
      </dialog>;
    }
    const creating = dialog.type === "create";
    const pending = pendingId === (creating ? "create" : dialog.workspace.id);
    return <dialog className="workspace-dialog" open aria-labelledby="workspace-name-dialog-title" onCancel={closeDialog} onClick={(event) => { if (event.target === event.currentTarget) closeDialog(); }}>
      <form className="workspace-dialog-card" onSubmit={submitName}>
        <div className="dialog-heading"><h2 id="workspace-name-dialog-title">{creating ? "Create workspace" : "Rename workspace"}</h2><button type="button" className="icon-button" aria-label={`Close ${creating ? "create" : "rename"} workspace dialog`} disabled={pending} onClick={closeDialog}>×</button></div>
        <label>Workspace name<input value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Product research" autoFocus disabled={pending} /></label>
        <p className="dialog-note">Workspaces keep documents and chats separate.</p>
        {formError && <p className="form-error" role="alert">{formError}</p>}
        <div className="dialog-actions"><button type="button" className="text-button" disabled={pending} onClick={closeDialog}>Cancel</button><button className="primary-button" disabled={pending}>{pending ? (creating ? "Creating…" : "Saving…") : (creating ? "Create workspace" : "Save name")}</button></div>
      </form>
    </dialog>;
  }

  const screenError = (status === "archived" ? error : "") || (!dialog ? formError : "");

  return <main className="workspace-manager">
    <header className="workspace-manager-header">
      <h1>Workspaces</h1>
      <div className="workspace-manager-tools">
        <label className="workspace-search">
          <span className="sr-only">Search workspaces</span>
          <svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m15.5 15.5 4 4" /></svg>
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search workspaces" />
        </label>
        <button className="workspace-new-button" onClick={() => openNameDialog("create")}>New</button>
      </div>
    </header>
    <div className="workspace-tabs" role="tablist" aria-label="Workspace status">
      <button role="tab" aria-selected={status === "active"} onClick={() => { setStatus("active"); setMenuId(null); setFormError(""); }}>Active</button>
      <button role="tab" aria-selected={status === "archived"} onClick={() => void selectArchivedTab()}>Archived</button>
    </div>
    {screenError && <p className="workspace-screen-error" role="alert">{screenError}</p>}
    <section className="workspace-table" aria-live="polite" aria-busy={loading}>
      <div className="workspace-table-heading"><span>Name</span><span>Modified</span><span>Actions</span></div>
      {!loading && visibleWorkspaces.map(renderWorkspaceRow)}
      {(loading || visibleWorkspaces.length === 0) && renderEmptyState()}
    </section>
    {renderDialog()}
  </main>;
}
