"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { DocumentFileType, DocumentStatus, KnowledgeDocument } from "@/types/api";
import { formatFileSize } from "@/lib/document-validation";
import { useDeleteDocument, useDocuments } from "@/hooks/use-documents";
import { DeleteDocumentDialog, documentStatusLabels, documentTypeLabels, DocumentStatusBadge } from "@/components/documents/document-ui";
import { UploadDocumentDialog } from "@/components/documents/upload-document-dialog";

const statuses = Object.keys(documentStatusLabels) as DocumentStatus[];
const fileTypes = Object.keys(documentTypeLabels) as DocumentFileType[];

export function DocumentList() {
  const router = useRouter(); const pathname = usePathname(); const params = useSearchParams();
  const [search, setSearch] = useState(params.get("search") ?? "");
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<KnowledgeDocument | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const rawPage = Number(params.get("page") ?? "1"); const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1; const pageSize = 10;
  const rawStatus = params.get("status"); const status = statuses.includes(rawStatus as DocumentStatus) ? rawStatus as DocumentStatus : undefined;
  const rawFileType = params.get("file_type"); const fileType = fileTypes.includes(rawFileType as DocumentFileType) ? rawFileType as DocumentFileType : undefined;
  useEffect(() => { const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 350); return () => window.clearTimeout(timer); }, [search]);
  useEffect(() => {
    const current = params.get("search") ?? "";
    if (current === debouncedSearch) return;
    const next = new URLSearchParams(params.toString());
    if (debouncedSearch) next.set("search", debouncedSearch); else next.delete("search");
    next.set("page", "1"); router.replace(`${pathname}?${next}`);
  }, [debouncedSearch, params, pathname, router]);
  const filters = { page, pageSize, search: debouncedSearch || undefined, status, fileType };
  const query = useDocuments(filters);
  const remove = useDeleteDocument(deleting?.id ?? "");
  const setFilter = (key: string, value: string, resetPage = true) => { const next = new URLSearchParams(params.toString()); if (value) next.set(key, value); else next.delete(key); if (resetPage) next.set("page", "1"); router.push(`${pathname}?${next}`); };
  const clearFilters = () => { setSearch(""); router.push(pathname); };
  const confirmDelete = async () => { if (!deleting) return; setDeleteError(null); try { await remove.mutateAsync(); setDeleting(null); setNotice("Document deleted."); } catch { setDeleteError("The document could not be deleted. Check storage access and try again."); } };
  const hasFilters = Boolean(debouncedSearch || status || fileType);
  return <div className="document-workspace"><div className="knowledge-heading"><div><p className="eyebrow">Approved sources</p><h1 className="page-title">Knowledge Base</h1><p className="page-description">Manage the documents that ground accurate support responses.</p></div><button className="primary-button" onClick={() => { setNotice(null); setUploadOpen(true); }}>Upload Document</button></div>{notice && <div className="success-notice" role="status">{notice}</div>}<div className="document-toolbar"><input className="search-input" aria-label="Search documents" placeholder="Search by title or filename" value={search} onChange={(event) => setSearch(event.target.value)} /><label className="filter-field">Status<select aria-label="Status filter" value={status ?? ""} onChange={(event) => setFilter("status", event.target.value)}><option value="">All statuses</option>{statuses.map((item) => <option value={item} key={item}>{documentStatusLabels[item]}</option>)}</select></label><label className="filter-field">File type<select aria-label="File type filter" value={fileType ?? ""} onChange={(event) => setFilter("file_type", event.target.value)}><option value="">All types</option>{fileTypes.map((item) => <option value={item} key={item}>{documentTypeLabels[item]}</option>)}</select></label><button className="secondary-button" disabled={!hasFilters} onClick={clearFilters}>Clear filters</button></div>{query.isLoading ? <DocumentListSkeleton /> : query.isError ? <div className="document-state"><h2>Documents could not load</h2><p>Check the backend connection and try again.</p><button className="secondary-button" onClick={() => query.refetch()}>Retry</button></div> : <DocumentResults items={query.data!.items} total={query.data!.total} page={page} pageSize={query.data!.page_size} hasFilters={hasFilters} onPage={(nextPage) => setFilter("page", String(nextPage), false)} onDelete={(document) => { setDeleteError(null); setDeleting(document); }} />}<UploadDocumentDialog open={uploadOpen} onClose={() => setUploadOpen(false)} onComplete={(processingFailed) => { setUploadOpen(false); setNotice(processingFailed ? "Document uploaded, but processing failed. It remains available for reprocessing." : "Document uploaded and processed successfully."); }} />{deleting && <DeleteDocumentDialog document={deleting} open busy={remove.isPending} error={deleteError} onCancel={() => setDeleting(null)} onConfirm={confirmDelete} />}</div>;
}

function DocumentResults({ items, total, page, pageSize, hasFilters, onPage, onDelete }: { items: KnowledgeDocument[]; total: number; page: number; pageSize: number; hasFilters: boolean; onPage: (page: number) => void; onDelete: (document: KnowledgeDocument) => void }) {
  if (items.length === 0) return <div className="document-state"><h2>{hasFilters ? "No documents match your filters" : "Your knowledge base is empty"}</h2><p>{hasFilters ? "Try a different search or clear the filters." : "Upload a PDF, Markdown, or TXT document to get started."}</p></div>;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  return <><div className="document-table-wrap"><table className="document-table"><thead><tr><th>Document</th><th>Type & size</th><th>Status</th><th>Version</th><th>Chunks</th><th>Uploaded</th><th>Actions</th></tr></thead><tbody>{items.map((document) => <tr key={document.id}><td><Link href={`/knowledge-base/${document.id}`}><strong>{document.title}</strong><span>{document.original_filename}</span></Link></td><td><strong>{documentTypeLabels[document.file_type]}</strong><span>{formatFileSize(document.file_size_bytes)}</span></td><td><DocumentStatusBadge status={document.status} /></td><td>{document.version}</td><td>{document.chunk_count}</td><td>{new Date(document.created_at).toLocaleDateString()}</td><td><div className="row-actions"><Link className="text-button" href={`/knowledge-base/${document.id}`}>View</Link><button className="text-button text-danger" disabled={document.status === "processing"} onClick={() => onDelete(document)}>Delete</button></div></td></tr>)}</tbody></table></div><div className="document-cards">{items.map((document) => <article className="document-card" key={document.id}><div className="document-card-top"><DocumentStatusBadge status={document.status} /><span>{documentTypeLabels[document.file_type]} · {formatFileSize(document.file_size_bytes)}</span></div><Link href={`/knowledge-base/${document.id}`}><h2>{document.title}</h2><p>{document.original_filename}</p></Link><dl><div><dt>Version</dt><dd>{document.version}</dd></div><div><dt>Chunks</dt><dd>{document.chunk_count}</dd></div><div><dt>Uploaded</dt><dd>{new Date(document.created_at).toLocaleDateString()}</dd></div></dl><div className="row-actions"><Link className="text-button" href={`/knowledge-base/${document.id}`}>View details</Link><button className="text-button text-danger" disabled={document.status === "processing"} onClick={() => onDelete(document)}>Delete</button></div></article>)}</div><div className="pagination"><button className="secondary-button" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button><span>Page {page} of {pageCount}</span><button className="secondary-button" disabled={page >= pageCount} onClick={() => onPage(page + 1)}>Next</button></div></>;
}

function DocumentListSkeleton() { return <div className="document-skeleton" aria-label="Loading documents">{Array.from({ length: 6 }, (_, index) => <div key={index} />)}</div>; }
