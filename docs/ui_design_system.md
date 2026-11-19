# ProcureIQ interface design system

The React application uses one light/dark design system across Command Center, Spend Explorer, Investigations, Strategy Studio, Data Operations and Reports. The redesign changes presentation and interaction; FastAPI contracts, source selection, calculations and persisted investigation content remain authoritative.

## Foundation and tokens

`apps/web/src/styles.css` is the single Tailwind 4 entry point. It imports Tailwind, restrained transition utilities, retained structural styles in `legacy.css`, then the new system in `design.css`. This ordering matters: tokens and new workspace rules must be processed by Tailwind and override retained rules. New work should use the semantic tokens, shared components and workspace classes rather than extending old shell rules.

| Token | Light | Dark | Purpose |
|---|---|---|---|
| `--canvas` | `#f5f5f2` | `#10151e` | Warm application canvas |
| `--card` | `#ffffff` | `#1b2230` | Cards, drawers and dialogs |
| `--foreground` | `#1d2939` | `#ecedf4` | Primary text |
| `--muted-foreground` | `#6b7483` | `#a0aabd` | Secondary information |
| `--primary` | `#5259d6` | `#9296ff` | Actions, selection and chart emphasis |
| `--primary-foreground` | White | `#10151e` | Text on primary actions |
| `--border` | `#e7e9ed` | `#323b4c` | Quiet boundaries |
| `--success` | `#158064` | `#5ac9a4` | Successful recorded operations |
| `--warning` | `#a66a12` | `#edbd67` | Review context |
| `--destructive` | `#c3474d` | `#f28b90` | Errors and destructive outcomes |

Cards use a 14px radius, controls approximately 8px, and a restrained shadow. Spacing follows a 4px rhythm with 16/24/32px composition gaps. The system font stack starts with Inter when locally installed, then platform sans-serif fonts; no external font service is requested. Main headings are approximately 28px desktop/25px mobile, body text 14px and secondary labels generally 12px. Financial strings retain exact API digits; chart coordinates, priority rounding, heatmap intensity and percentage widths are presentation only.

## Shared components and navigation

The actual shadcn-derived primitives live in `components/ui/`. `Design.tsx` composes metric cards, case cards, panels, section headers, tooltips, action links and detail drawers. Existing `Common.tsx` centralizes pagination, errors, source warnings and the Radix dialog wrapper. `product/shared.tsx` retains bounded API retrieval, scope controls, metrics, lazy charts and real download handling.

`AppShell.tsx` provides grouped route navigation, desktop collapse-to-icons, a mobile Sheet drawer, actual reporting-period context, API connection state and a theme toggle. The command palette searches eight implemented route destinations; it does not claim to search source records. Cmd/Ctrl+K opens it. Theme and collapse preferences use local storage, with safe fallback if storage is unavailable. Query navigation history uses session storage. There are no invented users, organizations or notifications.

The command palette, Reports, Operations and Optimization are split into lazy chunks. Recharts remains independently loaded. The shell and charts use the same semantic colors in both themes.

## Workspace composition

- **Command Center:** asymmetric dashboard with one emphasized expenditure card, operational case context, ranked reviews, a recent-activity timeline and actual pipeline state. Empty states invite real actions rather than implying missing data is a successful result.
- **Spend Explorer:** scope toolbar and removable chips; Overview, Categories, Suppliers, Transactions and Concentration tabs. Supplier cards open real detail routes. The original-source drawer presents published fields first and technical lineage on demand. Transaction search/order/page controls still use the backend.
- **Investigations:** two-panel review queue, searchable case cards, compact case header and metrics, accessible workspace tabs, structured overview, evidence drawer, persisted finding cards, citation inspection, an icon timeline and a lifecycle confirmation dialog.
- **Strategy Studio:** explicit baseline binding; exact assumption inputs with supplementary percentage sliders; independent comparison cards, sensitivity shading and break-even threshold. The optimizer separates demand, constraints, candidate inputs, solving, comparison and saved results. Its allocation bar is derived only from actual solver shares.
- **Data Operations:** recorded status cards, run list, version cards and a stage timeline. Durations, states and outputs come from the API; there is no synthetic percentage progress. Source activation retains confirmation and server checks.
- **Reports:** scope and inclusion configuration, case selector, content chips, executive findings, expandable recommendations, source-basis context and dedicated PowerPoint/JSON/Excel export cards.

## Demo presentation and evidence integrity

Only case titles matching the explicit, case-insensitive leading prefix `^\s*\[LOCAL DEMO\]` count as demos. Other titles are never inferred to be demonstrations. `lib/presentation.ts` supplies display-only titles. The original title is available under “Original saved title”; the original objective, findings and audit trail are preserved.

Command Center and Saved Cases hide demos by default and offer “Show demo cases”. Counts explicitly identify loaded cases and demo inclusion. Case search and demo filtering operate on the current bounded page, not a fabricated global search. Pagination totals remain backend totals including demos. Command Center uses the first 50 case records and marks a partial active count with `+` when additional pages exist. The report selector shows up to 100 saved cases and retains exact-ID input for other records. Genuine HMRC reviews remain visible regardless of demo settings.

## Accessibility and responsive behavior

Radix supplies dialog/Sheet modality, focus containment and Escape handling; cmdk supplies keyboard command selection. Tab triggers and panels are paired through the actual Tabs primitive. Controls retain labels, native table headings, focus indicators and textual status labels. Destructive and lifecycle operations retain explicit confirmation; toast notifications supplement persistent success/error feedback.

Desktop navigation becomes a mobile drawer. Cards reflow, charts resize, and wide source/input/sensitivity tables scroll within their own containers. Detail drawers and lifecycle dialogs are bounded by the viewport. Reduced-motion rules suppress decorative transitions; chart animations are disabled. Keyboard, focus, mobile and dark-theme checks are documented in [redesign verification](product_redesign_verification.md). This is not a formal third-party accessibility certification.
