import { describe, expect, it } from "vitest";
import { MAX_DOCUMENT_SIZE, validateDocumentFile } from "@/lib/document-validation";

describe("document file validation", () => {
  it("requires a file", () => expect(validateDocumentFile(null)).toBe("Choose a document file."));
  it.each(["guide.pdf", "guide.md", "guide.txt"])("accepts %s", (name) => expect(validateDocumentFile(new File(["content"], name))).toBeNull());
  it("rejects unsupported extensions", () => expect(validateDocumentFile(new File(["content"], "guide.docx"))).toMatch(/PDF, Markdown, or TXT/));
  it("rejects files larger than 5 MiB", () => expect(validateDocumentFile(new File([new Uint8Array(MAX_DOCUMENT_SIZE + 1)], "large.pdf"))).toMatch(/5 MiB/));
});
