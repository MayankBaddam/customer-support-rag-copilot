"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/components/auth/auth-provider";
import { deleteDocument, getDocument, getDocumentChunks, getDocuments, processDocument, reprocessDocument, uploadDocument, type DocumentFilters } from "@/lib/api-client";

export function useDocuments(filters: DocumentFilters) {
  const { session } = useAuth();
  return useQuery({ queryKey: ["documents", filters], queryFn: () => getDocuments(session!.access_token, filters), enabled: Boolean(session) });
}

export function useDocument(documentId: string) {
  const { session } = useAuth();
  return useQuery({ queryKey: ["document", documentId], queryFn: () => getDocument(session!.access_token, documentId), enabled: Boolean(session) });
}

export function useDocumentChunks(documentId: string, page: number) {
  const { session } = useAuth();
  return useQuery({ queryKey: ["document-chunks", documentId, page], queryFn: () => getDocumentChunks(session!.access_token, documentId, page), enabled: Boolean(session) });
}

export function useUploadDocument() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ title, file }: { title: string; file: File }) => uploadDocument(session!.access_token, title, file),
    onSuccess: (document) => {
      queryClient.setQueryData(["document", document.id], document);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useUploadAndProcessDocument() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ title, file }: { title: string; file: File }) => {
      const document = await uploadDocument(session!.access_token, title, file);
      try {
        return { document: await processDocument(session!.access_token, document.id), processingFailed: false };
      } catch {
        return { document, processingFailed: true };
      }
    },
    onSettled: (result) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      if (result?.document.id) queryClient.invalidateQueries({ queryKey: ["document", result.document.id] });
    },
  });
}

export function useProcessDocument(documentId: string, reprocess = false) {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => reprocess ? reprocessDocument(session!.access_token, documentId) : processDocument(session!.access_token, documentId),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["document", documentId] });
      queryClient.invalidateQueries({ queryKey: ["document-chunks", documentId] });
    },
  });
}

export function useDeleteDocument(documentId: string) {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteDocument(session!.access_token, documentId),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["document", documentId] });
      queryClient.removeQueries({ queryKey: ["document-chunks", documentId] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
