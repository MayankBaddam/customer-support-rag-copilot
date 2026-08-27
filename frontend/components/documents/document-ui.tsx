"use client";

import { useEffect, useRef } from "react";
import type { DocumentFileType, DocumentStatus, KnowledgeDocument } from "@/types/api";

export const documentStatusLabels: Record<DocumentStatus, string> = { pending: "Pending", processing: "Processing", completed: "Completed", failed: "Failed", archived: "Archived" };
export const documentTypeLabels: Record<DocumentFileType, string> = { pdf: "PDF", markdown: "Markdown", text: "TXT" };

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  return <span className={`document-badge document-badge-${status}`} aria-label={`Status: ${documentStatusLabels[status]}`}>{status === "processing" && <span className="badge-spinner" aria-hidden="true" />}{documentStatusLabels[status]}</span>;
}

export function DeleteDocumentDialog({ document, open, busy, error, onCancel, onConfirm }: { document: KnowledgeDocument; open: boolean; busy: boolean; error: string | null; onCancel: () => void; onConfirm: () => void }) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (open) cancelRef.current?.focus(); }, [open]);
  if (!open) return null;
  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onCancel(); }}><section className="document-dialog confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-document-title"><p className="eyebrow">Permanent action</p><h2 id="delete-document-title">Delete {document.title}?</h2><p>This removes <strong>{document.original_filename}</strong> and its processed chunks. This action cannot be undone.</p>{error && <p className="form-error" role="alert">{error}</p>}<div className="dialog-actions"><button ref={cancelRef} className="secondary-button" disabled={busy} onClick={onCancel}>Cancel</button><button className="danger-button" disabled={busy} onClick={onConfirm}>{busy ? "Deleting..." : "Delete document"}</button></div></section></div>;
}
