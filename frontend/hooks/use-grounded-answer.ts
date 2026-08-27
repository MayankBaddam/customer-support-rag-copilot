"use client";

import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@/components/auth/auth-provider";
import { generateGroundedAnswer } from "@/lib/api-client";
import type { SemanticSearchRequest } from "@/types/api";

export function useGroundedAnswer() {
  const { session } = useAuth();
  return useMutation({
    mutationFn: (request: SemanticSearchRequest) => generateGroundedAnswer(session!.access_token, request),
    throwOnError: false,
  });
}
