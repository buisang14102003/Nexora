import { ChangeEvent, FormEvent, useState } from "react";

import type { ChatMessage, WorkspaceDocument } from "../api/client";

export function ChatView({ workspaceName, documents, messages, isStreaming, error, onUpload, onSend }: { workspaceName: string | null; documents: WorkspaceDocument[]; messages: ChatMessage[]; isStreaming: boolean; error: string; onUpload: (files: FileList) => Promise<void>; onSend: (question: string) => Promise<void> }) {
  const [question, setQuestion] = useState("");
  const isEmpty = messages.length === 0;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = question.trim();
    if (!value || isStreaming) return;
    setQuestion("");
    await onSend(value);
  }

  function upload(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files?.length) void onUpload(event.target.files);
    event.target.value = "";
  }

  return (
    <main className={`chat-panel ${isEmpty ? "is-empty" : ""}`}>
      <header className="chat-header"><div><p className="eyebrow">Workspace</p><h1>{workspaceName ?? "Chọn workspace"}</h1></div></header>
      <section className="transcript" aria-live="polite">
        {!workspaceName && <div className="empty-state"><h2>Bắt đầu với workspace</h2><p>Tạo hoặc chọn một workspace ở thanh bên trái.</p></div>}
        {workspaceName && isEmpty && <div className="empty-state"><h2>Bạn muốn tìm gì?</h2><p>Hỏi về tài liệu trong workspace này hoặc thêm tài liệu vào context.</p>{documents.length > 0 && <ul className="document-list">{documents.map((document) => <li key={document.id}><span className="document-name">{document.original_filename}</span><span className="document-status">{document.status}</span></li>)}</ul>}</div>}
        {messages.map((message, index) => <article className={`message ${message.role}`} key={message.id ?? `${message.role}-${index}`}>
          <span className="message-role">{message.role === "user" ? "Bạn" : "RAG"}</span>
          <p>{message.content || (isStreaming && message.role === "assistant" ? "Đang trả lời…" : "")}</p>
          {message.citations.length > 0 && <ul className="citations">{message.citations.map((citation, citationIndex) => <li key={`${citation.document_id}-${citationIndex}`}>{citation.source_name}{citation.page_number ? ` · trang ${citation.page_number}` : ""}{citation.row_range ? ` · hàng ${citation.row_range}` : ""}</li>)}</ul>}
        </article>)}
        {error && <p className="stream-error" role="alert">{error}</p>}
      </section>
      <form className="composer" onSubmit={submit}>
        <label className="attachment-button" aria-label="Thêm tài liệu">Attach<input type="file" accept=".pdf,.docx,.csv,image/png,image/jpeg" multiple onChange={upload} disabled={!workspaceName || isStreaming} /></label>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={workspaceName ? "Hỏi về tài liệu trong workspace" : "Chọn workspace để bắt đầu"} disabled={!workspaceName || isStreaming} rows={1} />
        <button className="send-button" disabled={!workspaceName || isStreaming || !question.trim()}>{isStreaming ? "…" : "Send"}</button>
      </form>
    </main>
  );
}
