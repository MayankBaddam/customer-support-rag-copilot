export const MAX_DOCUMENT_SIZE = 5 * 1024 * 1024;
const allowedExtensions = new Set([".pdf", ".md", ".txt"]);

export function validateDocumentFile(file: File | null): string | null {
  if (!file) return "Choose a document file.";
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!allowedExtensions.has(extension)) return "Choose a PDF, Markdown, or TXT file.";
  if (file.size > MAX_DOCUMENT_SIZE) return "The file must be 5 MiB or smaller.";
  return null;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}
