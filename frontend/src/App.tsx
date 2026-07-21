import { useEffect, useMemo, useState } from "react";

import { ApiError, ChatMessage, ChatSession, createApiClient, signIn, signUp, Workspace, WorkspaceDocument } from "./api/client";
import { clearToken, readToken, saveToken } from "./auth/token";
import { AuthView } from "./components/AuthView";
import { ChatView } from "./components/ChatView";
import { Sidebar } from "./components/Sidebar";

export default function App() {
  const [token, setToken] = useState(readToken);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documents, setDocuments] = useState<WorkspaceDocument[]>([]);
  const [error, setError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const api = useMemo(() => (token ? createApiClient(token) : null), [token]);
  const activeWorkspace = workspaces.find((workspace) => workspace.id === workspaceId) ?? null;

  function handleApiError(reason: unknown) {
    const message = reason instanceof Error ? reason.message : "Không thể hoàn tất yêu cầu.";
    setError(message);
    if (reason instanceof ApiError && reason.status === 401) logout();
  }

  async function loadWorkspaces(preferredId?: string) {
    if (!api) return;
    try {
      const nextWorkspaces = await api.listWorkspaces();
      setWorkspaces(nextWorkspaces);
      const nextWorkspaceId = preferredId ?? (workspaceId && nextWorkspaces.some((workspace) => workspace.id === workspaceId) ? workspaceId : nextWorkspaces[0]?.id ?? null);
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

  async function authenticate(email: string, password: string, mode: "signin" | "signup") {
    const nextToken = mode === "signin" ? await signIn(email, password) : await signUp(email, password);
    saveToken(nextToken);
    setToken(nextToken);
  }

  function logout() {
    clearToken();
    setToken(null);
    setError("");
  }

  async function createWorkspace(name: string) {
    if (!api) return;
    const workspace = await api.createWorkspace(name);
    setWorkspaces((current) => [workspace, ...current]);
    setWorkspaceId(workspace.id);
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
    const title = window.prompt("Tên hội thoại", session.title)?.trim();
    if (!title || title === session.title) return;
    try {
      const renamed = await api.renameSession(workspaceId, session.id, title);
      setSessions((current) => current.map((item) => item.id === renamed.id ? renamed : item));
    } catch (reason) {
      handleApiError(reason);
    }
  }

  async function deleteSession(session: ChatSession) {
    if (!api || !workspaceId || !window.confirm(`Xóa “${session.title}”?`)) return;
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

  return <div className="app-shell">
    <Sidebar workspaces={workspaces} activeWorkspaceId={workspaceId} sessions={sessions} activeSessionId={sessionId} onSelectWorkspace={setWorkspaceId} onCreateWorkspace={createWorkspace} onNewChat={newChat} onSelectSession={selectSession} onRenameSession={renameSession} onDeleteSession={deleteSession} onLogout={logout} />
    <ChatView workspaceName={activeWorkspace?.name ?? null} documents={documents} messages={messages} isStreaming={streaming} error={error} onUpload={uploadDocuments} onSend={send} />
  </div>;
}
