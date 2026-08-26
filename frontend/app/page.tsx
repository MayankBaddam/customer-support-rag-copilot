import { AppShell } from "@/components/layout/app-shell";
import { PageIntro } from "@/components/layout/page-intro";

export default function Home() {
  return (
    <AppShell>
      <PageIntro
        eyebrow="Workspace overview"
        title="Good morning, support team"
        description="Your CloudDesk workspace is ready for the next customer conversation."
      />
      <section className="dashboard-grid" aria-label="Workspace summary">
        <article className="metric-panel metric-panel-accent">
          <p className="metric-label">Open tickets</p>
          <p className="metric-value">24</p>
          <p className="metric-note">Across all support queues</p>
        </article>
        <article className="metric-panel">
          <p className="metric-label">Knowledge base</p>
          <p className="metric-value">48</p>
          <p className="metric-note">Approved source documents</p>
        </article>
        <article className="metric-panel">
          <p className="metric-label">Response health</p>
          <p className="metric-value">94%</p>
          <p className="metric-note">Within target this week</p>
        </article>
      </section>
      <section className="welcome-panel">
        <div>
          <p className="section-kicker">Today&apos;s focus</p>
          <h2>Keep every answer clear, sourced, and human-reviewed.</h2>
          <p>Use the navigation to explore tickets, approved knowledge, and evaluation results.</p>
        </div>
        <span className="welcome-mark" aria-hidden="true">CD</span>
      </section>
    </AppShell>
  );
}
