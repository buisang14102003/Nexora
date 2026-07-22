import { ChangeEvent, useRef } from "react";

import type { WorkspaceDocument } from "../api/client";

export function KnowledgeView({ workspaceName, documents, onUpload }: { workspaceName: string | null; documents: WorkspaceDocument[]; onUpload: (files: FileList) => Promise<void> }) {
  const inputRef = useRef<HTMLInputElement>(null);
  function upload(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files?.length) void onUpload(event.target.files);
    event.target.value = "";
  }
  return <section className="knowledge-panel">
    <header><p className="eyebrow">Knowledge base</p><h2>{workspaceName ?? "Select a workspace"}</h2></header>
    <input ref={inputRef} className="file-input" type="file" accept=".pdf,.docx,.csv,image/png,image/jpeg" multiple onChange={upload} disabled={!workspaceName} />
    <button className="upload-dropzone" type="button" disabled={!workspaceName} onClick={() => inputRef.current?.click()}><strong>Upload knowledge</strong><span>Click to upload PDF, DOCX, CSV, or images</span></button>
    <div className="knowledge-list"><div className="knowledge-list-header"><span>File name</span><span>Status</span></div>{documents.length ? documents.map((document) => <div className="knowledge-row" key={document.id}><span>{document.original_filename}</span><small className={document.status}>{document.status}</small></div>) : <p className="knowledge-empty">Uploaded documents will appear here.</p>}</div>
  </section>;
}
