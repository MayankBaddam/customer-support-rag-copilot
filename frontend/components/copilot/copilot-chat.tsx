"use client";

import { useState, type FormEvent } from "react";
import { ApiErrorState } from "@/components/errors/api-error-state";
import { useGroundedAnswer } from "@/hooks/use-grounded-answer";

const topKOptions = Array.from({ length: 10 }, (_, index) => index + 1);

export function CopilotChat() {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const answer = useGroundedAnswer();
  const normalizedQuestion = question.trim();

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!normalizedQuestion || answer.isPending) return;
    try {
      await answer.mutateAsync({ query: normalizedQuestion, top_k: topK });
    } catch {
      // React Query exposes the safe error state below.
    }
  };

  return <div className="copilot-workspace">
    <div className="retrieval-heading">
      <p className="eyebrow">Knowledge-grounded support</p>
      <h1 className="page-title">Copilot</h1>
      <p className="page-description">Answers are based only on your uploaded knowledge documents.</p>
    </div>

    <form className="retrieval-form" onSubmit={submit}>
      <label className="retrieval-query-field">
        Question
        <textarea
          aria-label="Question"
          maxLength={1000}
          placeholder="How long does a password recovery link remain valid?"
          rows={4}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
      </label>
      <label className="retrieval-top-k">
        Sources
        <select aria-label="Top sources" value={topK} onChange={(event) => setTopK(Number(event.target.value))}>
          {topKOptions.map((value) => <option value={value} key={value}>{value}</option>)}
        </select>
      </label>
      <button className="primary-button" type="submit" disabled={!normalizedQuestion || answer.isPending}>
        {answer.isPending ? "Generating..." : "Ask Copilot"}
      </button>
    </form>

    {answer.isPending && <div className="retrieval-state" role="status"><h2>Finding grounded evidence</h2><p>Searching your uploaded documents and preparing a supported answer.</p></div>}
    {answer.isError && <ApiErrorState error={answer.error} fallbackTitle="Copilot could not answer" fallbackMessage="The request could not be completed. Please try again." />}
    {answer.isSuccess && <section className="copilot-response" aria-label="Copilot answer">
      <article className="copilot-answer-card">
        <div className="copilot-answer-heading"><p className="eyebrow">Grounded answer</p><span>{answer.data.retrieved_chunks} chunk{answer.data.retrieved_chunks === 1 ? "" : "s"} retrieved</span></div>
        <p className="copilot-answer-text">{answer.data.answer}</p>
      </article>

      {answer.data.citations.length > 0 ? <div className="copilot-citations" aria-label="Citations">
        <div className="section-heading"><h2>Supporting citations</h2><span>{answer.data.citations.length} source{answer.data.citations.length === 1 ? "" : "s"}</span></div>
        <div className="retrieval-list">
          {answer.data.citations.map((citation, index) => <article className="retrieval-card" key={citation.chunk_id}>
            <div className="retrieval-card-heading">
              <div><p className="eyebrow">Citation {index + 1}</p><h2>{citation.document_title}</h2><p>{citation.original_filename}</p></div>
              <div className="similarity-score"><span>Similarity</span><strong>{citation.similarity_score.toFixed(4)}</strong></div>
            </div>
            <div className="retrieval-meta">
              <span>Section: {citation.section_title ?? "Not specified"}</span>
              {citation.page_number !== null && <span>Page: {citation.page_number}</span>}
            </div>
          </article>)}
        </div>
      </div> : <div className="copilot-no-citations"><h2>No supporting citations</h2><p>No knowledge-base chunks supported this answer.</p></div>}
    </section>}
    {!answer.isPending && !answer.isError && !answer.isSuccess && <div className="retrieval-state">
      <h2>Ready for a grounded answer</h2>
      <p>Ask one support question. Copilot will use only evidence from your uploaded documents.</p>
    </div>}
  </div>;
}
