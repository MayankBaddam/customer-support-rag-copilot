import { AppShell } from "@/components/layout/app-shell";
import { DocumentDetail } from "@/components/documents/document-detail";

export default async function DocumentDetailPage({ params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  return <AppShell><DocumentDetail documentId={documentId} /></AppShell>;
}
