import { TooltipProvider } from "../components/ui/tooltip";
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as client from "../api/client";
import { Optimization } from "../product/Optimization";
import { Operations } from "../product/Operations";
import { CaseWork } from "../product/CaseWork";
import { ErrorBoundary } from "../components/ErrorBoundary";
import type { ReactNode } from "react";
function mount(node: ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <MemoryRouter>
        <TooltipProvider>{node}</TooltipProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
const page = {
  groups: [],
  all_total: 0,
  items: [],
  total: 0,
  offset: 0,
  limit: 50,
};
describe("Product workflows", () => {
  it("submits explicit optimizer assumptions and distinguishes an infeasible solver outcome", async () => {
    const req = vi.spyOn(client, "request").mockImplementation(async (path) =>
      path === "/strategy/optimization/solve"
        ? {
            status: "infeasible",
            allocations: [],
            binding_constraints: [],
            explanations: ["Capacity below demand"],
            objective_gbp: null,
            feasible: false,
            validation: {},
          }
        : (page as never),
    );
    mount(<Optimization />);
    await userEvent.click(
      screen.getByRole("button", { name: "Load clearly illustrative example" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "4 · Optimize and compare" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Run optimization" }),
    );
    expect(
      await screen.findByRole("heading", {
        name: "Solver outcome: Infeasible",
      }),
    ).toBeInTheDocument();
    const call = req.mock.calls.find(
      (x) => x[0] === "/strategy/optimization/solve",
    );
    expect(call?.[2]).toMatchObject({ demand: "100", dependency_pct: "60" });
    expect(screen.getByText("Capacity below demand")).toBeInTheDocument();
  });
  it("writes an analyst note, invalidates the list and renders persisted content", async () => {
    let saved = false;
    const req = vi
      .spyOn(client, "request")
      .mockImplementation(async (path, _signal, body) => {
        if (path.includes("/bookmarks")) return page as never;
        if (body) {
          saved = true;
          return { entry_id: 1 } as never;
        }
        return {
          ...page,
          total: saved ? 1 : 0,
          items: saved
            ? [
                {
                  entry_id: 1,
                  kind: "note",
                  title: "Analyst observation",
                  content: "Independent source review is required.",
                  row_version: 1,
                  citations: [],
                },
              ]
            : [],
        } as never;
      });
    mount(<CaseWork id="4" closed={false} />);
    await userEvent.click(screen.getByRole("button", { name: "Notes" }));
    await userEvent.click(screen.getByRole("button", { name: "New Note" }));
    await userEvent.selectOptions(screen.getByLabelText("Entry kind"), "note");
    await userEvent.type(screen.getByLabelText("Title"), "Analyst observation");
    await userEvent.type(
      screen.getByLabelText("Observation / original reasoning"),
      "Independent source review is required.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Save entry" }));
    expect(
      await screen.findByRole("heading", { name: "Analyst observation" }),
    ).toBeInTheDocument();
    expect(req.mock.calls.find((c) => c[2])?.[2]).toMatchObject({
      kind: "note",
      citations: [],
      expected_version: null,
    });
  });
  it("blocks closed case editing and exposes persisted evidence separately", async () => {
    vi.spyOn(client, "request").mockResolvedValue(page);
    mount(<CaseWork id="4" closed />);
    expect(
      screen.queryByRole("button", { name: "Save entry" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/Reopen with a written reason/),
    ).toBeInTheDocument();
  });
  it("queues actual verification and does not manufacture successful runs", async () => {
    const req = vi
      .spyOn(client, "request")
      .mockImplementation(async (path, _signal, body) =>
        body
          ? ({ run_id: 7, status: "queued" } as never)
          : path.includes("manifests")
            ? ({ items: [] } as never)
            : (page as never),
      );
    mount(<Operations />);
    await userEvent.click(
      screen.getByRole("button", { name: "Run read-only verification" }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Queued run #7",
    );
    await waitFor(() =>
      expect(req.mock.calls.find((c) => c[2])?.[2]).toMatchObject({
        operation: "verify",
        confirm_activation: false,
      }),
    );
    expect(screen.queryByText("succeeded")).not.toBeInTheDocument();
  });
  it("contains unexpected render failures with a recovery action", () => {
    function Broken(): ReactNode {
      throw Error("fixture");
    }
    vi.spyOn(console, "error").mockImplementation(() => {});
    mount(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "This workspace could not render",
    );
  });
});

import { Command } from "../product/Command";
import { Spend } from "../product/Spend";
import { Scenarios, ProductState } from "../product/Strategy";
import { Reports } from "../product/Reports";
vi.mock("../product/Charts", () => ({
  default: () => <div>Chart fixture</div>,
}));
describe("Analytical and reporting workspaces", () => {
  it("shows exact command totals and actionable case counts", async () => {
    vi.spyOn(client, "request").mockImplementation(async (path) =>
      path === "/command"
        ? ({
            overview: [
              {
                positive_gbp: "1234567.89",
                credit_gbp: "2.00",
                net_gbp: "1234565.89",
                record_count: 3,
              },
            ],
            months: [],
            case_counts: { OPEN: 2 },
            activity: [],
          } as never)
        : path.includes("reviews")
          ? ({
              ...page,
              exported_count: 0,
              qualified_count: 0,
              deferred_count: 0,
            } as never)
          : (page as never),
    );
    mount(<Command />);
    expect(await screen.findByTitle("£1,234,567.89")).toBeInTheDocument();
    expect(screen.getByText("Active investigations")).toBeInTheDocument();
    expect(
      screen.getByText("Open, investigating or reviewed · current workspace"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "All investigations" }),
    ).toHaveAttribute("href", "/investigations/cases");
  });
  it("keeps empty spend results explicit and changes to server transaction search", async () => {
    const req = vi.spyOn(client, "request").mockImplementation(async (path) =>
      path.startsWith("/spend/summary")
        ? ({
            overview: [
              {
                positive_gbp: "0",
                credit_gbp: "0",
                net_gbp: "0",
                record_count: 0,
              },
            ],
            monthly: [],
            concentration: [],
            source_fingerprint: "a".repeat(64),
          } as never)
        : path.includes("options")
          ? ({ options: {} } as never)
          : (page as never),
    );
    mount(<Spend />);
    await screen.findByRole("tab", { name: "Transactions" });
    await userEvent.click(screen.getByRole("tab", { name: "Transactions" }));
    await userEvent.type(
      screen.getByLabelText("Search transactions"),
      "needle",
    );
    expect(
      await screen.findByText("No transactions match this scope and search."),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(req.mock.calls.some((c) => c[0].includes("search=needle"))).toBe(
        true,
      ),
    );
  });
  it("binds a baseline explicitly and keeps assumptions editable without browser financial arithmetic", async () => {
    const req = vi.spyOn(client, "request").mockImplementation(async (path) =>
      path.includes("options")
        ? ({ options: {} } as never)
        : ({
            kind: "manual",
            amount_gbp: "1000000",
            scope: "Synthetic baseline",
            period_label: "Selected test period",
            filters: {},
            limitation: "Hypothetical fixture",
          } as never),
    );
    mount(
      <ProductState>
        <Scenarios />
      </ProductState>,
    );
    await userEvent.selectOptions(
      screen.getByLabelText("Baseline source"),
      "manual",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Use selected baseline" }),
    );
    expect(await screen.findByText("£1,000,000.00")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", {
        name: "Load illustrative examples (not validated rates)",
      }),
    );
    expect(screen.getByLabelText("Base Improvement %")).toHaveValue("2");
    expect(req.mock.calls.some((c) => c[0] === "/strategy/calculate")).toBe(
      false,
    );
  });
  it("requires report preview before enabling artifact download and shows recoverable API errors", async () => {
    vi.spyOn(client, "request").mockImplementation(async (path) => {
      if (path.includes("preview")) throw new client.ApiError("stale_source");
      return path.includes("/cases")
        ? (page as never)
        : ({ options: {} } as never);
    });
    mount(
      <ProductState>
        <Reports />
      </ProductState>,
    );
    expect(
      screen.queryByRole("button", { name: "Download five-slide PowerPoint" }),
    ).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Continue to evidence" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Review executive brief" }),
    );
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});

it("opens a finding citation using its frozen case classification and ordinal", async () => {
  const req = vi.spyOn(client, "request").mockImplementation(async (path) =>
    path.includes("/evidence?")
      ? ({
          ...page,
          items: [
            {
              source_values: { Supplier: "Original supplier", Amount: "42" },
              filename: "original.csv",
              file_sha256: "f".repeat(64),
              source_record_number: 9,
              raw_row_id: 12,
              classification: "contextual",
              ordinal: 51,
            },
          ],
        } as never)
      : path.includes("/entries")
        ? ({
            ...page,
            total: 1,
            items: [
              {
                entry_id: 1,
                kind: "finding",
                title: "Saved finding",
                content: "Preserved conclusion",
                citations: [{ classification: "contextual", ordinal: 51 }],
              },
            ],
          } as never)
        : (page as never),
  );
  mount(<CaseWork id="4" closed />);
  await userEvent.click(
    await screen.findByRole("button", { name: "contextual #51 ↗" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Original supplier" }),
  ).toBeInTheDocument();
  expect(
    req.mock.calls.some(
      (c) =>
        c[0] ===
        "/investigations/cases/4/evidence?classification=contextual&offset=50&limit=1",
    ),
  ).toBe(true);
});

it("renders transaction detail from original source_values rather than assuming typed fields", async () => {
  vi.spyOn(client, "request").mockImplementation(async (path) =>
    path.includes("/summary")
      ? ({
          overview: [],
          monthly: [],
          concentration: [],
          source_fingerprint: "a".repeat(64),
        } as never)
      : path.includes("/options")
        ? ({ options: {} } as never)
        : path.startsWith("/spend/transactions?")
          ? ({
              ...page,
              total: 1,
              items: [
                {
                  raw_row_id: 9,
                  supplier_raw: "Frozen supplier",
                  amount_gbp: "12.34",
                },
              ],
            } as never)
          : ({
              record: {
                reporting_month: "2025-04-01",
                filename: "original.csv",
                source_values: {
                  Supplier: "Frozen supplier",
                  Amount: "£12.34",
                  Date: "01/04/2025",
                  "Expense type": "Published category",
                  "Transaction number": "000019",
                },
              },
            } as never),
  );
  mount(<Spend />);
  await userEvent.click(
    await screen.findByRole("tab", { name: "Transactions" }),
  );
  await userEvent.click(
    await screen.findByRole("button", { name: "Inspect #9" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Frozen supplier" }),
  ).toBeInTheDocument();
  expect(screen.getByText("000019")).toBeInTheDocument();
  expect(screen.getByText("Published category")).toBeInTheDocument();
});
