import { ChangeEvent, FormEvent, useRef, useState } from "react";

import type { ChatMessage, WorkspaceDocument } from "../api/client";

export function ChatView({ workspaceName, documents, messages, isStreaming, error, onUpload, onSend }: { workspaceName: string | null; documents: WorkspaceDocument[]; messages: ChatMessage[]; isStreaming: boolean; error: string; onUpload: (files: FileList) => Promise<void>; onSend: (question: string) => Promise<void> }) {
  const [question, setQuestion] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isEmpty = messages.length === 0;
  const readyDocuments = documents.filter((document) => document.status === "ready");
  const pendingDocuments = documents.filter((document) => document.status === "queued" || document.status === "processing");

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
      <header className="chat-header"><div><p className="eyebrow">Workspace</p><h1>{workspaceName ?? "Select a workspace"}</h1></div></header>
      <section className="transcript" aria-live="polite">
        {!workspaceName && <div className="empty-state"><h2>Start with a workspace</h2><p>Create or select a workspace from the sidebar.</p></div>}
        {workspaceName && isEmpty && <div className="empty-state"><h2>{readyDocuments.length ? "What would you like to know?" : "Add a document to get started"}</h2><p>{readyDocuments.length ? "Ask a specific question about the ready documents in this workspace." : pendingDocuments.length ? "Your document is being prepared. You can ask questions once its status is ready." : "Upload a PDF, DOCX, CSV, or image to start a grounded conversation."}</p>{documents.length > 0 && <ul className="document-list">{documents.map((document) => <li key={document.id}><span className="document-name">{document.original_filename}</span><span className={`document-status ${document.status}`}>{document.status}</span></li>)}</ul>}</div>}
        {messages.map((message, index) => <article className={`message ${message.role}`} key={message.id ?? `${message.role}-${index}`}>
          <span className="message-role">{message.role === "user" ? "You" : "RAG"}</span>
          <p>{message.content || (isStreaming && message.role === "assistant" ? "Thinking…" : "")}</p>
          {message.citations.length > 0 && <ul className="citations">{message.citations.map((citation, citationIndex) => <li key={`${citation.document_id}-${citationIndex}`}>{citation.source_name}{citation.page_number ? ` · page ${citation.page_number}` : ""}{citation.row_range ? ` · rows ${citation.row_range}` : ""}</li>)}</ul>}
        </article>)}
        {error && <p className="stream-error" role="alert">{error}</p>}
      </section>
      <form className="composer" onSubmit={submit}>
        <input ref={fileInputRef} className="file-input" type="file" accept=".pdf,.docx,.csv,image/png,image/jpeg" multiple onChange={upload} disabled={!workspaceName || isStreaming} />
        <button className="attachment-button" type="button" aria-label="Add documents" onClick={() => fileInputRef.current?.click()} disabled={!workspaceName || isStreaming}>Attach</button>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={workspaceName ? "Ask about your documents" : "Select a workspace to begin"} disabled={!workspaceName || isStreaming} rows={1} />
        <button className="send-button" disabled={!workspaceName || isStreaming || !question.trim()}>{isStreaming ? "…" : "Send"}</button>
      </form>
      {workspaceName && documents.length > 0 && <div className="document-context" aria-label="Document context">{documents.map((document) => <span key={document.id} className={`document-chip ${document.status}`}>{document.original_filename} <small>{document.status}</small></span>)}</div>}
    </main>
  );
}
