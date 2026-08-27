"use client";

import { useState } from "react";
import { useDocumentChunks } from "@/hooks/use-documents";

const COLLAPSE_AT = 420;

export function ChunkPreview({ documentId }: { documentId: string }) {
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const query = useDocumentChunks(documentId, page);
  if (query.isLoading) return <section className="chunk-panel"><h2>Chunk preview</h2><div className="chunk-skeleton" aria-label="Loading chunks" /></section>;
  if (query.isError) return <section className="chunk-panel"><h2>Chunk preview</h2><div className="inline-state"><p>Chunks could not load.</p><button className="secondary-button" onClick={() => query.refetch()}>Retry</button></div></section>;
  const data = query.data!; const pageCount = Math.max(1, Math.ceil(data.total / data.page_size));
  return <section className="chunk-panel"><div className="section-heading"><div><p className="section-kicker">Extracted content</p><h2>Chunk preview</h2></div><span>{data.total} chunks</span></div>{data.items.length === 0 ? <div className="inline-state"><p>No chunks are available for this document.</p></div> : <div className="chunk-list">{data.items.map((chunk) => { const isLong = chunk.content.length > COLLAPSE_AT; const isExpanded = expanded.has(chunk.id); const content = isLong && !isExpanded ? `${chunk.content.slice(0, COLLAPSE_AT)}…` : chunk.content; return <article className="chunk-card" key={chunk.id}><div className="chunk-meta"><strong>Chunk {chunk.chunk_index}</strong>{chunk.page_number && <span>Page {chunk.page_number}</span>}{chunk.section_title && <span>{chunk.section_title}</span>}<span>{chunk.token_count} tokens</span></div><p>{content}</p>{isLong && <button className="text-button" aria-expanded={isExpanded} onClick={() => setExpanded((current) => { const next = new Set(current); if (next.has(chunk.id)) next.delete(chunk.id); else next.add(chunk.id); return next; })}>{isExpanded ? "Show less" : "Show more"}</button>}</article>; })}</div>}{pageCount > 1 && <div className="pagination"><button className="secondary-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous chunks</button><span>Page {page} of {pageCount}</span><button className="secondary-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next chunks</button></div>}</section>;
}
