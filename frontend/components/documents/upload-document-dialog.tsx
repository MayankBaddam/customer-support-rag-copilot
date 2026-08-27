"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiClientError } from "@/lib/api-client";
import { formatFileSize, validateDocumentFile } from "@/lib/document-validation";
import { useUploadAndProcessDocument } from "@/hooks/use-documents";

export function UploadDocumentDialog({ open, onClose, onComplete }: { open: boolean; onClose: () => void; onComplete: (processingFailed: boolean) => void }) {
  const titleRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mutation = useUploadAndProcessDocument();
  useEffect(() => { if (open) titleRef.current?.focus(); }, [open]);
  if (!open) return null;
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(null);
    if (!title.trim()) { setError("Enter a document title."); return; }
    const fileError = validateDocumentFile(file);
    if (fileError) { setError(fileError); return; }
    try {
      const result = await mutation.mutateAsync({ title: title.trim(), file: file! });
      setTitle(""); setFile(null); onComplete(result.processingFailed);
    } catch (caught) {
      setError(caught instanceof ApiClientError ? caught.message : "The document could not be uploaded.");
    }
  }
  return <div className="dialog-backdrop" role="presentation"><section className="document-dialog" role="dialog" aria-modal="true" aria-labelledby="upload-document-title"><div className="dialog-heading"><div><p className="eyebrow">New source</p><h2 id="upload-document-title">Upload document</h2></div><button className="dialog-close" aria-label="Close upload dialog" disabled={mutation.isPending} onClick={onClose}>×</button></div><form className="document-form" onSubmit={submit}><label>Title<input ref={titleRef} value={title} disabled={mutation.isPending} onChange={(event) => setTitle(event.target.value)} /></label><label>File<input type="file" accept=".pdf,.md,.txt,application/pdf,text/markdown,text/plain" disabled={mutation.isPending} onChange={(event) => { const selected = event.target.files?.[0] ?? null; setFile(selected); setError(validateDocumentFile(selected)); }} /></label>{file && <div className="selected-file"><strong>{file.name}</strong><span>{file.type || "Unknown type"} · {formatFileSize(file.size)}</span></div>}<p className="field-help">PDF, Markdown, or TXT. Maximum 5 MiB.</p>{error && <p className="form-error" role="alert">{error}</p>}<div className="dialog-actions"><button type="button" className="secondary-button" disabled={mutation.isPending} onClick={onClose}>Cancel</button><button className="primary-button" disabled={mutation.isPending}>{mutation.isPending ? "Uploading and processing..." : "Upload document"}</button></div></form></section></div>;
}
