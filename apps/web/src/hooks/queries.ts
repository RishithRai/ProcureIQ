import { useNamespace } from "../lib/workspace";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
export function useHealth() {
  const namespace = useNamespace();
  return useQuery({
    queryKey: ["health", namespace],
    queryFn: ({ signal }) => api.health(signal),
    staleTime: 30000,
  });
}
export function useReviews(query: string, offset: number, enabled: boolean) {
  const namespace = useNamespace();
  return useQuery({
    queryKey: ["reviews", "list", query, offset, namespace],
    queryFn: ({ signal }) =>
      api.reviews(`${query}&offset=${offset}&limit=50`, signal),
    enabled,
  });
}
export function useReview(id: string, reporting: string, enabled: boolean) {
  const namespace = useNamespace();
  return useQuery({
    queryKey: ["reviews", "detail", id, reporting, namespace],
    queryFn: ({ signal }) => api.review(id, reporting, signal),
    enabled,
  });
}
export function useCases(query: string, enabled: boolean) {
  const namespace = useNamespace();
  return useQuery({
    queryKey: ["cases", query, namespace],
    queryFn: ({ signal }) => api.cases(query, signal),
    enabled,
  });
}
export function useCase(id: string, enabled: boolean) {
  const namespace = useNamespace();
  return useQuery({
    queryKey: ["case", id, namespace],
    queryFn: ({ signal }) => api.case(id, signal),
    enabled,
  });
}
export function useEvidence(
  id: string,
  classification: string,
  offset: number,
) {
  const namespace = useNamespace();
  return useQuery({
    queryKey: ["evidence", id, classification, offset, namespace],
    queryFn: ({ signal }) => api.evidence(id, classification, offset, signal),
  });
}
export function useActivity(id: string, offset: number) {
  const namespace = useNamespace();
  return useQuery({
    queryKey: ["activity", id, offset, namespace],
    queryFn: ({ signal }) => api.activity(id, offset, signal),
  });
}
