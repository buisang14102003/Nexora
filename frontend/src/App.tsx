import { useEffect, useMemo, useState } from "react";

import { ApiError, ChatMessage, ChatSession, createApiClient, signIn, signUp, Workspace, WorkspaceDocument, WorkspaceUpdate } from "./api/client";
import { clearToken, readToken, saveToken } from "./auth/token";
import { AuthView } from "./components/AuthView";
import { ChatView } from "./components/ChatView";
import { KnowledgeView } from "./components/KnowledgeView";
import { Sidebar } from "./components/Sidebar";
import { WorkspaceManager } from "./components/WorkspaceManager";
import { nextWorkspaceAfterArchive, orderActiveWorkspaces } from "./workspaces/state";

type ContentMode = "workspace" | "manager";

export default function App() {
  const [token, setToken] = useState(readToken);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [archivedWorkspaces, setArchivedWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [contentMode, setContentMode] = useState<ContentMode>("workspace");
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [workspaceError, setWorkspaceError] = useState("");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documents, setDocuments] = useState<WorkspaceDocument[]>([]);
  const [error, setError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const api = useMemo(() => (token ? createApiClient(token) : null), [token]);
  const activeWorkspace = workspaces.find((workspace) => workspace.id === workspaceId) ?? null;
  const hasPendingDocuments = documents.some((document) => document.status === "queued" || document.status === "processing");

  function handleApiError(reason: unknown) {
    const message = reason instanceof Error ? reason.message : "We couldn't complete that request.";
    setError(message);
    if (reason instanceof ApiError && reason.status === 401) logout();
  }

  async function loadWorkspaces(preferredId?: string) {
    if (!api) return;
    try {
      const nextWorkspaces = await api.listWorkspaces();
      const orderedWorkspaces = orderActiveWorkspaces(nextWorkspaces);
      setWorkspaces(orderedWorkspaces);
      const nextWorkspaceId = preferredId ?? (workspaceId && orderedWorkspaces.some((workspace) => workspace.id === workspaceId) ? workspaceId : orderedWorkspaces[0]?.id ?? null);
      setWorkspaceId(nextWorkspaceId);
    } catch (reason) {
      handleApiError(reason);
    }
  }

  async function loadSessions(nextWorkspaceId: string) {
    if (!api) return;
    try {
      setError("");
      const nextSessions = await api.listSessions(nextWorkspaceId);
      setSessions(nextSessions);
      setSessionId(null);
      setMessages([]);
    } catch (reason) {
      handleApiError(reason);
    }
  }

  async function loadDocuments(nextWorkspaceId: string) {
    if (!api) return;
    try {
      setDocuments(await api.listDocuments(nextWorkspaceId));
    } catch (reason) {
      handleApiError(reason);
    }
  }

  useEffect(() => {
    if (api) void loadWorkspaces();
    else {
      setWorkspaces([]);
      setWorkspaceId(null);
      setSessions([]);
      setSessionId(null);
      setMessages([]);
      setDocuments([]);
    }
  }, [api]);

  useEffect(() => {
    if (workspaceId) {
      void loadSessions(workspaceId);
      void loadDocuments(workspaceId);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (!workspaceId || !hasPendingDocuments) return;
    const timer = window.setTimeout(() => void loadDocuments(workspaceId), 2_000);
    return () => window.clearTimeout(timer);
  }, [workspaceId, hasPendingDocuments]);

  async function authenticate(email: string, password: string, mode: "signin" | "signup") {
    const nextToken = mode === "signin" ? await signIn(email, password) : await signUp(email, password);
    saveToken(nextToken);
    setToken(nextToken);
  }

  function logout() {
    clearToken();
    setToken(null);
    setWorkspaces([]);
    setArchivedWorkspaces([]);
    setWorkspaceId(null);
    setContentMode("workspace");
    setWorkspaceLoading(false);
    setWorkspaceError("");
    setError("");
  }

  async function createWorkspace(name: string) {
    if (!api) return;
    const workspace = await api.createWorkspace(name);
    setWorkspaces((current) => orderActiveWorkspaces([workspace, ...current]));
    setWorkspaceId(workspace.id);
    setContentMode("workspace");
  }

  async function loadArchivedWorkspaces() {
    if (!api) return;
    setWorkspaceLoading(true);
    setWorkspaceError("");
    try {
      setArchivedWorkspaces(await api.listWorkspaces("archived"));
    } catch (reason) {
      setWorkspaceError(reason instanceof Error ? reason.message : "We couldn't load archived workspaces.");
    } finally {
      setWorkspaceLoading(false);
    }
  }

  function openWorkspace(nextWorkspaceId: string) {
    setWorkspaceId(nextWorkspaceId);
    setContentMode("workspace");
  }

  async function updateWorkspace(targetWorkspaceId: string, update: WorkspaceUpdate) {
    if (!api) return;
    const updated = await api.updateWorkspace(targetWorkspaceId, update);
    setWorkspaces((current) => orderActiveWorkspaces(current.map((workspace) => workspace.id === updated.id ? updated : workspace)));
  }

  async function archiveWorkspace(targetWorkspaceId: string) {
    if (!api) return;
    const archived = await api.archiveWorkspace(targetWorkspaceId);
    const remaining = orderActiveWorkspaces(workspaces.filter((workspace) => workspace.id !== targetWorkspaceId));
    const nextWorkspaceId = nextWorkspaceAfterArchive(workspaces, workspaceId, targetWorkspaceId);
    setWorkspaces(remaining);
    setArchivedWorkspaces((current) => [archived, ...current.filter((workspace) => workspace.id !== archived.id)]);
    if (targetWorkspaceId === workspaceId) {
      setWorkspaceId(nextWorkspaceId);
      if (!nextWorkspaceId) {
        setSessions([]);
        setSessionId(null);
        setMessages([]);
        setDocuments([]);
      }
    }
    setContentMode("manager");
  }

  async function restoreWorkspace(targetWorkspaceId: string) {
    if (!api) return;
    const restored = await api.restoreWorkspace(targetWorkspaceId);
    setArchivedWorkspaces((current) => current.filter((workspace) => workspace.id !== targetWorkspaceId));
    setWorkspaces((current) => orderActiveWorkspaces([restored, ...current]));
  }

  async function uploadDocuments(files: FileList) {
    if (!api || !workspaceId) return;
    try {
      setError("");
      const uploaded = await Promise.all(Array.from(files).map((file) => api.uploadDocument(workspaceId, file)));
      setDocuments((current) => [...uploaded, ...current]);
    } catch (reason) {
      handleApiError(reason);
    }
  }

  async function newChat(): Promise<ChatSession | null> {
    if (!api || !workspaceId) return null;
    try {
      setError("");
      const session = await api.createSession(workspaceId);
      setSessions((current) => [session, ...current]);
      setSessionId(session.id);
      setMessages([]);
      return session;
    } catch (reason) {
      handleApiError(reason);
      return null;
    }
  }

  async function selectSession(nextSessionId: string) {
    if (!api || !workspaceId) return;
    try {
      setError("");
      const detail = await api.getSession(workspaceId, nextSessionId);
      setSessionId(nextSessionId);
      setMessages(detail.messages);
    } catch (reason) {
      handleApiError(reason);
    }
  }

  async function renameSession(session: ChatSession) {
    if (!api || !workspaceId) return;
    const title = window.prompt("Chat title", session.title)?.trim();
    if (!title || title === session.title) return;
    try {
      const renamed = await api.renameSession(workspaceId, session.id, title);
      setSessions((current) => current.map((item) => item.id === renamed.id ? renamed : item));
    } catch (reason) {
      handleApiError(reason);
    }
  }

  async function deleteSession(session: ChatSession) {
    if (!api || !workspaceId || !window.confirm(`Delete “${session.title}”?`)) return;
    try {
      await api.deleteSession(workspaceId, session.id);
      setSessions((current) => current.filter((item) => item.id !== session.id));
      if (session.id === sessionId) {
        setSessionId(null);
        setMessages([]);
      }
    } catch (reason) {
      handleApiError(reason);
    }
  }

  async function send(question: string) {
    if (!api || !workspaceId || streaming) return;
    setError("");
    let activeSessionId = sessionId;
    if (!activeSessionId) {
      const session = await newChat();
      if (!session) return;
      activeSessionId = session.id;
    }
    const provisionalAssistant: ChatMessage = { role: "assistant", content: "", citations: [] };
    setMessages((current) => [...current, { role: "user", content: question, citations: [] }, provisionalAssistant]);
    setStreaming(true);
    try {
      await api.streamChat(
        workspaceId,
        question,
        activeSessionId,
        (update) => setMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, content: update.replace ? update.answer ?? "" : message.content + (update.delta ?? "") } : message)),
        (citations) => setMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, citations } : message)),
      );
      await selectSession(activeSessionId);
      const refreshed = await api.listSessions(workspaceId);
      setSessions(refreshed);
    } catch (reason) {
      setMessages((current) => current.filter((_, index) => index !== current.length - 1));
      handleApiError(reason);
    } finally {
      setStreaming(false);
    }
  }

  if (!token) return <AuthView onSubmit={authenticate} />;

  return <div className={contentMode === "manager" ? "app-shell manager-mode" : "app-shell"}>
    <Sidebar
      workspaces={workspaces}
      activeWorkspaceId={workspaceId}
      managerActive={contentMode === "manager"}
      sessions={sessions}
      activeSessionId={sessionId}
      onOpenManager={() => setContentMode("manager")}
      onSelectWorkspace={openWorkspace}
      onNewChat={async () => {
        setContentMode("workspace");
        return newChat();
      }}
      onSelectSession={selectSession}
      onRenameSession={renameSession}
      onDeleteSession={deleteSession}
      onLogout={logout}
    />
    {contentMode === "manager" ? <WorkspaceManager
      activeWorkspaces={workspaces}
      archivedWorkspaces={archivedWorkspaces}
      loading={workspaceLoading}
      error={workspaceError}
      onLoadArchived={loadArchivedWorkspaces}
      onCreate={createWorkspace}
      onOpen={openWorkspace}
      onUpdate={updateWorkspace}
      onArchive={archiveWorkspace}
      onRestore={restoreWorkspace}
    /> : <>
      <KnowledgeView workspaceName={activeWorkspace?.name ?? null} documents={documents} onUpload={uploadDocuments} />
      <ChatView workspaceName={activeWorkspace?.name ?? null} documents={documents} messages={messages} isStreaming={streaming} error={error} onUpload={uploadDocuments} onSend={send} />
    </>}
  </div>;
}
