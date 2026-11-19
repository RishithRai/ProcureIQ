# UI component sources and licensing

Inspected on 16 October 2026. The application incorporates selected free source components, not a purchased template. The primary system is shadcn/ui's Radix-based registry adapted to the existing React/Vite/Tailwind 4 project.

## Components actually incorporated

The following source files were downloaded, read and adapted from the [shadcn/ui new-york-v4 registry](https://github.com/shadcn-ui/ui/tree/main/apps/v4/registry/new-york-v4/ui). Each local file contains an attribution header. The complete [MIT notice](../apps/web/licenses/shadcn-ui.txt), copyright 2023 shadcn, is retained in the repository.

| Component | Exact source | Actual application use |
|---|---|---|
| Button | [button.tsx](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/button.tsx) | Shell, case actions and navigation links |
| Card | [card.tsx](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/card.tsx) | MetricCard, Panel and dashboard composition |
| Badge | [badge.tsx](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/badge.tsx) | Demo, source, solver and report-content indicators |
| Tabs | [tabs.tsx](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/tabs.tsx) | Spend Explorer and case detail, including associated panels |
| Dialog | [dialog.tsx](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/dialog.tsx) | Case creation, lifecycle and command menu |
| Sheet | [sheet.tsx](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/sheet.tsx) | Mobile navigation, transactions, evidence and citations |
| Command | [command.tsx](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/command.tsx) | Real route palette, Cmd/Ctrl+K |
| Tooltip | [tooltip.tsx](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/tooltip.tsx) | Contextual exposure interpretation and shared Hint primitive |
| Skeleton | [skeleton.tsx](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/skeleton.tsx) | API loading state, with screen-reader status text |

Adaptations: local relative imports and `cn` utility; semantic CSS tokens; Vite/Tailwind processing; the command dialog's accessible title/description moved inside its content; shorter Sheet transitions; application-specific drawer dimensions and responsive controls. The custom shell composes these primitives rather than copying a complete sidebar/dashboard block. Original-layout code remains distinct from copied primitives.

Package APIs and installed license texts were inspected, not guessed. Versions are locked in `apps/web/package-lock.json`:

| Added dependency | License | Purpose |
|---|---|---|
| `radix-ui` 1.8.1 | MIT, WorkOS | Accessible Dialog, Tabs, Slot and Tooltip primitives |
| `cmdk` 1.1.1 | MIT, Paco Coursey | Command search and keyboard selection |
| `sonner` 2.0.8 | MIT, Emil Kowalski | Actual save, lifecycle and bookmark notifications |
| `class-variance-authority` 0.7.1 | Apache-2.0 | Shared button/badge variants |
| `clsx` 2.1.1 | MIT | Conditional class composition |
| `tailwind-merge` 3.7.0 | MIT | Tailwind class conflict resolution |
| `tw-animate-css` 1.4.0 | MIT, Wombosvideo | Primitive enter/exit transitions, with reduced-motion overrides |

Upstream package sources: [Radix](https://github.com/radix-ui/primitives), [cmdk](https://github.com/pacocoursey/cmdk), [Sonner](https://github.com/emilkowalski/sonner), [CVA](https://github.com/joe-bell/cva), [clsx](https://github.com/lukeed/clsx), [tailwind-merge](https://github.com/dcastil/tailwind-merge), [tw-animate-css](https://github.com/Wombosvideo/tw-animate-css). Full installed license notices remain in their npm packages. Existing Lucide icons, Recharts, React Router and TanStack Query were reused; no second chart framework or competing primitive system was installed.

## Research and selection decisions

All six requested resources were inspected before the redesign foundation was built. Further relevant component documentation/source was examined while refining the layouts:

- [21st.dev](https://21st.dev/) and its [community component catalogue](https://21st.dev/community/components): inspected available card, bento, button and toolbar patterns. No community snippet was copied without a component-specific license; no subscription or generated paid asset was used.
- [shadcn/ui](https://ui.shadcn.com/), [blocks](https://ui.shadcn.com/blocks), Dialog, Sidebar and Command documentation: selected the directly inspected Radix registry files above rather than introducing the separate Base UI variant used in some current documentation. The [repository license](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md) was read and retained.
- [ReUI](https://reui.io/) and [Stepper documentation](https://reui.io/docs/components/base/stepper): inspected controlled-step examples, API and Base/Radix variants. Its full wizard was unnecessary for the existing server-enforced lifecycle. The application uses its own presentational lifecycle indicator and the verified shadcn Dialog; no ReUI code or paid blocks were copied.
- [Magic UI](https://magicui.design/) and [Bento Grid](https://magicui.design/docs/components/bento-grid): inspected example source, imports and composition. Its marketing-oriented demo dependencies and hover effects were not needed. The dashboard bento layout is original CSS composition. No Magic UI code/assets were copied.
- [Tremor](https://tremor.so/) and [Category Bar](https://www.tremor.so/docs/visualizations/category-bar): inspected the actual CategoryBar source/API, marker calculation, color utilities and Tooltip dependency. Retained existing Recharts and implemented a small, explicitly labelled allocation-share view directly from solver outputs instead of installing another analytics system. No Tremor code was copied.

This is a deliberate component selection, not a claim that all researched libraries are installed. Only the nine attributed shadcn source files and listed runtime dependencies are incorporated. No paywall was bypassed, no entire template was imported, and no remote publishing capability was introduced.
