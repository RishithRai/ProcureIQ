import type { Case } from "../api/types";
export const isDemo = (c: Pick<Case, "title" | "namespace">) =>
  c.namespace === "DEMO";
export function caseTitle(
  c: Pick<Case, "title" | "review_snapshot" | "namespace">,
) {
  if (!isDemo(c)) return c.title;
  const origin = c.review_snapshot?.title;
  if (typeof origin === "string") return origin;
  return c.title
    .replace(/^\s*\[LOCAL DEMO\]\s*/i, "")
    .replace(/^Stage \d+ acceptance\s*[—–-]\s*/i, "")
    .replace(/^Complete product acceptance\s*[—–-]\s*/i, "");
}
