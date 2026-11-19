export const label = (s: string) =>
  (s === s.toUpperCase() ? s.toLowerCase() : s)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/Gbp/g, "GBP")
    .replace(/Pct/g, "%")
    .replace(/Hhi/g, "HHI");
// Decimal string formatting: no Number conversion or monetary arithmetic.
export function money(value: string) {
  const m = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value);
  if (!m) return value;
  return `${m[1]}£${m[2].replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${(m[3] || "").padEnd(2, "0")}`;
}
export const score = (value: string) => Number(value).toFixed(2); // Display only; never written back.
export const date = (value: string) =>
  new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
