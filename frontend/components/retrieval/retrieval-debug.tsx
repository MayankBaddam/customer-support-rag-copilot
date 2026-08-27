"use client";

import { useState, type FormEvent } from "react";
import { ApiErrorState } from "@/components/errors/api-error-state";
import { useSemanticSearch } from "@/hooks/use-semantic-search";

const topKOptions = Array.from({ length: 10 }, (_, index) => index + 1);

export function RetrievalDebug() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const search = useSemanticSearch();
  const normalizedQuery = query.trim();

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!normalizedQuery || search.isPending) return;
    try {
      await search.mutateAsync({ query: normalizedQuery, top_k: topK });
    } catch {
      // React Query exposes the safe error state below.
    }
  };

  return <div className="retrieval-workspace">
    <div className="retrieval-heading">
      <p className="eyebrow">Evidence inspection</p>
      <h1 className="page-title">Retrieval Debug</h1>
      <p className="page-description">Inspect the document chunks returned by semantic search before answer generation.</p>
    </div>

    <form className="retrieval-form" onSubmit={submit}>
      <label className="retrieval-query-field">
        Search query
        <textarea
          aria-label="Search query"
          maxLength={1000}
          placeholder="How long does a password recovery link remain valid?"
          rows={4}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <label className="retrieval-top-k">
        Results
        <select aria-label="Top results" value={topK} onChange={(event) => setTopK(Number(event.target.value))}>
          {topKOptions.map((value) => <option value={value} key={value}>{value}</option>)}
        </select>
      </label>
      <button className="primary-button" type="submit" disabled={!normalizedQuery || search.isPending}>
        {search.isPending ? "Searching..." : "Search"}
      </button>
    </form>

    {search.isPending && <div className="retrieval-state" role="status"><h2>Searching embedded knowledge</h2><p>Generating the query embedding and ranking matching chunks.</p></div>}
    {search.isError && <ApiErrorState error={search.error} fallbackTitle="Search could not be completed" fallbackMessage="Check the backend connection and try your search again." />}
    {search.isSuccess && search.data.results.length === 0 && <div className="retrieval-state">
      <h2>No matching evidence</h2>
      <p>Try a broader query or verify that completed documents have embeddings.</p>
    </div>}
    {search.isSuccess && search.data.results.length > 0 && <section className="retrieval-results" aria-label="Search results">
      <div className="retrieval-summary">
        <div><span>Evidence</span><strong>{search.data.result_count} result{search.data.result_count === 1 ? "" : "s"}</strong></div>
        <div><span>Retrieval latency</span><strong>{typeof search.data.retrieval_latency_ms === "number" ? `${search.data.retrieval_latency_ms.toFixed(2)} ms` : "Not reported"}</strong></div>
        <div><span>Embedding model</span><strong>{search.data.embedding_model}</strong></div>
      </div>
      <div className="retrieval-list">
        {search.data.results.map((result, index) => <article className="retrieval-card" key={result.chunk_id}>
          <div className="retrieval-card-heading">
            <div><p className="eyebrow">Result {index + 1}</p><h2>{result.document_title}</h2><p>{result.original_filename ?? "Original filename unavailable"}</p></div>
            <div className="similarity-score"><span>Similarity</span><strong>{result.similarity_score.toFixed(4)}</strong></div>
          </div>
          <div className="retrieval-meta">
            <span>Section: {result.section_title ?? "Not specified"}</span>
            {result.page_number !== null && <span>Page: {result.page_number}</span>}
          </div>
          <p className="retrieval-content">{result.content}</p>
        </article>)}
      </div>
    </section>}
    {!search.isPending && !search.isError && !search.isSuccess && <div className="retrieval-state">
      <h2>Ready to inspect retrieval</h2>
      <p>Enter a support question to see the highest-scoring embedded chunks.</p>
    </div>}
  </div>;
}
