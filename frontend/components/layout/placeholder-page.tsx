import { AppShell } from "@/components/layout/app-shell";
import { PageIntro } from "@/components/layout/page-intro";

export function PlaceholderPage({ eyebrow, title, description, note }: { eyebrow: string; title: string; description: string; note: string }) {
  return <AppShell><PageIntro eyebrow={eyebrow} title={title} description={description} /><section className="placeholder-panel"><p className="section-kicker">Phase 1 foundation</p><h2>{note}</h2><p>This area is ready for the next approved product phase.</p></section></AppShell>;
}