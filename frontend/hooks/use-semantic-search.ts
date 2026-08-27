"use client";

import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@/components/auth/auth-provider";
import { searchKnowledgeChunks } from "@/lib/api-client";
import type { SemanticSearchRequest } from "@/types/api";

export function useSemanticSearch() {
  const { session } = useAuth();
  return useMutation({
    mutationFn: (request: SemanticSearchRequest) => searchKnowledgeChunks(session!.access_token, request),
    throwOnError: false,
  });
}
