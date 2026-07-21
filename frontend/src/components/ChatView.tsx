import { ChangeEvent, FormEvent, useState } from "react";

import type { ChatMessage, WorkspaceDocument } from "../api/client";

export function ChatView({ workspaceName, documents, messages, isStreaming, error, onUpload, onSend }: { workspaceName: string | null; documents: WorkspaceDocument[]; messages: ChatMessage[]; isStreaming: boolean; error: string; onUpload: (files: FileList) => Promise<void>; onSend: (question: string) => Promise<void> }) {
  const [question, setQuestion] = useState("");

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
    <main className="chat-panel">
      <header className="chat-header"><div><p className="eyebrow">WORKSPACE</p><h1>{workspaceName ?? "Chọn workspace"}</h1></div>{workspaceName && <label className="upload-button">Thêm tài liệu<input type="file" accept=".pdf,.docx,.csv,image/png,image/jpeg" multiple onChange={upload} /></label>}</header>
      <section className="transcript" aria-live="polite">
        {!workspaceName && <div className="empty-state"><h2>Bắt đầu với workspace</h2><p>Tạo hoặc chọn một workspace ở thanh bên trái.</p></div>}
        {workspaceName && messages.length === 0 && <div className="empty-state"><h2>Chat mới</h2><p>Thêm PDF, DOCX, CSV hoặc ảnh rồi gửi câu hỏi về tài liệu trong workspace này.</p>{documents.length > 0 && <ul className="document-list">{documents.map((document) => <li key={document.id}>{document.original_filename} <span>{document.status}</span></li>)}</ul>}</div>}
        {messages.map((message, index) => <article className={`message ${message.role}`} key={message.id ?? `${message.role}-${index}`}>
          <span className="message-role">{message.role === "user" ? "Bạn" : "RAG"}</span>
          <p>{message.content || (isStreaming && message.role === "assistant" ? "Đang trả lời…" : "")}</p>
          {message.citations.length > 0 && <ul className="citations">{message.citations.map((citation, citationIndex) => <li key={`${citation.document_id}-${citationIndex}`}>{citation.source_name}{citation.page_number ? ` · trang ${citation.page_number}` : ""}{citation.row_range ? ` · hàng ${citation.row_range}` : ""}</li>)}</ul>}
        </article>)}
        {error && <p className="stream-error" role="alert">{error}</p>}
      </section>
      <form className="composer" onSubmit={submit}>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={workspaceName ? "Hỏi về tài liệu trong workspace…" : "Chọn workspace để bắt đầu"} disabled={!workspaceName || isStreaming} rows={3} />
        <button className="primary-button" disabled={!workspaceName || isStreaming || !question.trim()}>{isStreaming ? "Đang trả lời…" : "Gửi"}</button>
      </form>
    </main>
  );
}
