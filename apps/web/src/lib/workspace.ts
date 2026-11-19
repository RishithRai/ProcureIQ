import { useSyncExternalStore } from "react";
export type Namespace = "NORMAL" | "DEMO";
let mode: Namespace = "NORMAL";
try {
  if (sessionStorage.getItem("piq.namespace") === "DEMO") mode = "DEMO";
} catch {
  /* session-only fallback */
}
const listeners = new Set<() => void>();
export const getNamespace = () => mode;
export function setNamespace(next: Namespace) {
  mode = next;
  try {
    sessionStorage.setItem("piq.namespace", next);
  } catch {
    /* session-only fallback */
  }
  listeners.forEach((fn) => fn());
}
export function useNamespace() {
  return useSyncExternalStore((fn) => {
    listeners.add(fn);
    return () => {
      listeners.delete(fn);
    };
  }, getNamespace);
}

let writes = 0;
export function beginWrite() {
  writes++;
  listeners.forEach((fn) => fn());
  return () => {
    writes--;
    listeners.forEach((fn) => fn());
  };
}
export function usePendingWrites() {
  return useSyncExternalStore(
    (fn) => {
      listeners.add(fn);
      return () => {
        listeners.delete(fn);
      };
    },
    () => writes,
  );
}
