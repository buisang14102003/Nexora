const API_BASE_URL = "http://127.0.0.1:8100";

export type Workspace = {
  id: string;
  name: string;
  slug: string;
};

export type Citation = {
  document_id: string;
  source_name: string;
  page_number?: number | null;
  row_range?: string | null;
  chunk_id?: string | null;
};

export type ChatMessage = {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at?: string;
};

export type ChatSession = {
  id: string;
  workspace_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatSessionDetail = ChatSession & { messages: ChatMessage[] };

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

type Fetcher = typeof fetch;

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || `Yêu cầu thất bại (${response.status}).`;
  } catch {
    return `Yêu cầu thất bại (${response.status}).`;
  }
}

function parseSseBlocks(buffer: string, onEvent: (event: string, data: string) => void) {
  const blocks = buffer.split("\n\n");
  const remainder = blocks.pop() ?? "";

  for (const block of blocks) {
    const event = block.match(/^event: (.+)$/m)?.[1];
    const data = block.match(/^data: (.+)$/m)?.[1];
    if (event && data) onEvent(event, data);
  }
  return remainder;
}

export function createApiClient(token: string, fetcher: Fetcher = fetch) {
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetcher(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
    if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
    listWorkspaces: () => request<Workspace[]>("/workspaces"),
    createWorkspace: (name: string) =>
      request<Workspace>("/workspaces", { method: "POST", body: JSON.stringify({ name }) }),
    listSessions: (workspaceId: string) =>
      request<ChatSession[]>(`/workspaces/${workspaceId}/chat-sessions`),
    createSession: (workspaceId: string) =>
      request<ChatSession>(`/workspaces/${workspaceId}/chat-sessions`, { method: "POST" }),
    getSession: (workspaceId: string, sessionId: string) =>
      request<ChatSessionDetail>(`/workspaces/${workspaceId}/chat-sessions/${sessionId}`),
    renameSession: (workspaceId: string, sessionId: string, title: string) =>
      request<ChatSession>(`/workspaces/${workspaceId}/chat-sessions/${sessionId}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      }),
    deleteSession: (workspaceId: string, sessionId: string) =>
      request<void>(`/workspaces/${workspaceId}/chat-sessions/${sessionId}`, { method: "DELETE" }),
    async streamChat(
      workspaceId: string,
      question: string,
      sessionId: string,
      onAnswer: (update: { delta?: string; answer?: string; replace?: boolean }) => void,
      onCitations: (citations: Citation[]) => void,
    ) {
      const response = await fetcher(`${API_BASE_URL}/workspaces/${workspaceId}/chat`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: sessionId }),
      });
      if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
      if (!response.body) throw new ApiError(0, "Không nhận được luồng trả lời.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const handleEvent = (event: string, data: string) => {
        const payload = JSON.parse(data) as {
          delta?: string;
          answer?: string;
          replace?: boolean;
          citations?: Citation[];
        };
        if (event === "answer") onAnswer(payload);
        if (event === "citations") onCitations(payload.citations ?? []);
      };

      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        buffer = parseSseBlocks(buffer, handleEvent);
        if (done) break;
      }
      if (buffer.trim()) parseSseBlocks(`${buffer}\n\n`, handleEvent);
    },
  };
}

export async function signIn(email: string, password: string, fetcher: Fetcher = fetch): Promise<string> {
  const response = await fetcher(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return ((await response.json()) as { access_token: string }).access_token;
}

export async function signUp(email: string, password: string, fetcher: Fetcher = fetch): Promise<string> {
  const response = await fetcher(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return signIn(email, password, fetcher);
}
