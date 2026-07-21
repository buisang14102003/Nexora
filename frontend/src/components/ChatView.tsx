import { FormEvent, useState } from "react";

import type { ChatMessage } from "../api/client";

export function ChatView({ workspaceName, messages, isStreaming, error, onSend }: { workspaceName: string | null; messages: ChatMessage[]; isStreaming: boolean; error: string; onSend: (question: string) => Promise<void> }) {
  const [question, setQuestion] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = question.trim();
    if (!value || isStreaming) return;
    setQuestion("");
    await onSend(value);
  }

  return (
    <main className="chat-panel">
      <header className="chat-header"><div><p className="eyebrow">WORKSPACE</p><h1>{workspaceName ?? "Chọn workspace"}</h1></div></header>
      <section className="transcript" aria-live="polite">
        {!workspaceName && <div className="empty-state"><h2>Bắt đầu với workspace</h2><p>Tạo hoặc chọn một workspace ở thanh bên trái.</p></div>}
        {workspaceName && messages.length === 0 && <div className="empty-state"><h2>Chat mới</h2><p>Gửi câu hỏi để tìm câu trả lời trong tài liệu của workspace này.</p></div>}
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
