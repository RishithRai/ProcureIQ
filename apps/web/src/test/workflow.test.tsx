import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "../components/ui/tooltip";
import type { ReactNode } from "react";
import * as client from "../api/client";
import { setNamespace } from "../lib/workspace";
import { Command } from "../product/Command";
import { CaseEvidence } from "../pages/CaseEvidence";
import { CaseWork } from "../product/CaseWork";
import { Operations } from "../product/Operations";
import { Optimization } from "../product/Optimization";
import { Spend, Supplier } from "../product/Spend";
import { Reports } from "../product/Reports";
import { ProductState } from "../product/Strategy";
import evidence from "./evidence.json";
const empty = {
  items: [],
  total: 0,
  offset: 0,
  limit: 50,
  groups: [],
  all_total: 0,
};
function Location() {
  return (
    <output aria-label="location">
      {useLocation().pathname + useLocation().search}
    </output>
  );
}
function mount(node: ReactNode, path = "/") {
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <TooltipProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route
              path="*"
              element={
                <>
                  {node}
                  <Location />
                </>
              }
            />
            <Route
              path="/spend/suppliers/:supplierId"
              element={
                <>
                  {node}
                  <Location />
                </>
              }
            />
          </Routes>
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  );
}
vi.mock("../product/Charts", () => ({
  default: () => <div>Chart preview</div>,
}));
describe("Connected workflow refinement", () => {
  it("sends explicit namespaces and defaults back to NORMAL", async () => {
    const fetcher = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () => new Response("{}", { status: 200 }));
    setNamespace("DEMO");
    await client.request("/command");
    expect(fetcher.mock.calls[0][1]?.headers).toMatchObject({
      "X-Investigation-Namespace": "DEMO",
    });
    setNamespace("NORMAL");
    await client.request("/command");
    expect(fetcher.mock.calls[1][1]?.headers).toMatchObject({
      "X-Investigation-Namespace": "NORMAL",
    });
  });
  it("adapts first-time homepage without empty activity panels", async () => {
    vi.spyOn(client, "request").mockImplementation(
      async (path) =>
        (path === "/command"
          ? {
              overview: [{ positive_gbp: "1234567.89", record_count: 3 }],
              case_counts: {},
              activity: [],
              months: [],
            }
          : empty) as never,
    );
    mount(<Command />);
    expect(
      await screen.findByText("Start with a procurement review"),
    ).toBeVisible();
    expect(screen.queryByText("Recent activity")).not.toBeInTheDocument();
    expect(screen.getByTitle("£1,234,567.89")).toHaveTextContent("£1.23M");
  });
  it("distinguishes completed work from a first-time workspace", async () => {
    vi.spyOn(client, "request").mockImplementation(
      async (path) =>
        (path === "/command"
          ? {
              overview: [],
              case_counts: { CLOSED: 2 },
              activity: [],
              months: [],
            }
          : empty) as never,
    );
    mount(<Command />);
    expect(await screen.findByText("Completed work")).toBeVisible();
    expect(
      screen.queryByText("Start with a procurement review"),
    ).not.toBeInTheDocument();
  });
  it("filters frozen case evidence on the server and advances one record across boundaries", async () => {
    const req = vi.spyOn(client, "request").mockResolvedValue({
      ...evidence,
      unfiltered_total: 6497,
      items: [{ ...evidence.items[0], amount_gbp: "12.34", bookmarked: false }],
      total: 51,
    });
    mount(
      <CaseEvidence id="1" />,
      "/investigations/cases/1?tab=evidence&e_offset=50",
    );
    await userEvent.click(
      await screen.findByRole("button", { name: /Inspect source record/ }),
    );
    await waitFor(() =>
      expect(
        req.mock.calls.some((c) => c[0].includes("offset=50&limit=1")),
      ).toBe(true),
    );
    await userEvent.click(screen.getByRole("button", { name: "Previous" }));
    await waitFor(() =>
      expect(
        req.mock.calls.some((c) => c[0].includes("offset=49&limit=1")),
      ).toBe(true),
    );
    await userEvent.keyboard("{Escape}");
    await userEvent.type(
      screen.getByLabelText("Original supplier"),
      " Exact Ltd ",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Apply evidence filters" }),
    );
    await waitFor(() =>
      expect(
        req.mock.calls.some(
          (c) =>
            c[0].includes("supplier=+Exact+Ltd+") &&
            c[0].includes("offset=0&limit=50"),
        ),
      ).toBe(true),
    );
  });
  it("opens a focused finding editor with an explicitly passed bookmark citation", async () => {
    const req = vi.spyOn(client, "request").mockResolvedValue(empty);
    mount(
      <CaseWork id="1" closed={false} />,
      "/investigations/cases/1?tab=findings&citation=primary:51",
    );
    expect(await screen.findByRole("dialog")).toBeVisible();
    await userEvent.type(screen.getByLabelText("Title"), "Preliminary finding");
    await userEvent.type(
      screen.getByLabelText("Observation / original reasoning"),
      "Original source requires review.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Save entry" }));
    await waitFor(() =>
      expect(req.mock.calls.find((c) => c[2])?.[2]).toMatchObject({
        citations: [{ classification: "primary", ordinal: 51 }],
        sections: { assessment: "", next_step: "" },
      }),
    );
  });
  it("requires valid requirements before moving through the sourcing builder", async () => {
    vi.spyOn(client, "request").mockResolvedValue(empty);
    mount(<Optimization />);
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByRole("alert")).toHaveTextContent("positive quantity");
    expect(screen.queryByLabelText("Supplier 1 name")).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Load clearly illustrative example" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByLabelText("Supplier 1 Name")).toBeVisible();
  });
  it("exposes total quality records and sends issue filters with pagination reset", async () => {
    const req = vi.spyOn(client, "request").mockResolvedValue({
      ...empty,
      all_total: 1761,
      total: 1761,
      groups: [
        {
          issue_code: "repeated_identifier",
          severity: "warning",
          reporting_month: "2025-04-01",
          count: 1700,
        },
      ],
    });
    mount(<Operations />);
    await userEvent.click(screen.getByRole("tab", { name: "Data Quality" }));
    await userEvent.selectOptions(
      await screen.findByLabelText("Issue type"),
      "repeated_identifier",
    );
    await waitFor(() =>
      expect(
        req.mock.calls.some(
          (c) =>
            c[0].includes("issue_code=repeated_identifier") &&
            c[0].includes("offset=0"),
        ),
      ).toBe(true),
    );
    expect(screen.getByText(/1761 matching of 1761/)).toBeVisible();
  });
  it("carries exact category scope into transactions and financial modelling", async () => {
    vi.spyOn(client, "request").mockImplementation(
      async (path) =>
        (path.includes("/summary")
          ? {
              overview: [],
              monthly: [],
              concentration: [],
              source_fingerprint: "a".repeat(64),
            }
          : path.includes("expense_types")
            ? {
                ...empty,
                items: [
                  { group_value: " Exact category ", positive_gbp: "100" },
                ],
                total: 1,
              }
            : path.includes("/options")
              ? { options: {} }
              : empty) as never,
    );
    mount(<Spend />);
    await userEvent.click(
      await screen.findByRole("button", { name: /Exact category/ }),
    );
    expect(
      screen.getByRole("link", { name: "Build financial scenario" }),
    ).toHaveAttribute(
      "href",
      "/strategy/scenarios?expense_type=+Exact+category+",
    );
    expect(
      screen.getByRole("link", { name: "Matching transactions" }),
    ).toHaveAttribute(
      "href",
      "/spend?expense_type=+Exact+category+&tab=transactions",
    );
  });
  it("offers supplier month drilldown with supplier and exact month scope", async () => {
    vi.spyOn(client, "request").mockResolvedValue({
      supplier: { canonical_name: "Supplier A" },
      aliases: [],
      analytics: {
        overview: [{ positive_gbp: "100" }],
        monthly: [{ reporting_month: "2025-04-01" }],
        expense_types: [],
        expense_areas: [],
      },
      share_context: { share_all_positive_pct: "50" },
      concentration_context: [],
      filters: {},
    });
    mount(<Supplier />, "/spend/suppliers/31");
    expect(
      await screen.findByRole("link", { name: "2025-04" }),
    ).toHaveAttribute(
      "href",
      "/spend?supplier_id=31&tab=transactions&start_month=2025-04&end_month=2025-04",
    );
  });
  it("previews five dynamic generated slides and pins report content for downloads", async () => {
    const req = vi.spyOn(client, "request").mockImplementation(
      async (path) =>
        (path === "/reports/preview"
          ? {
              brief: {
                period: "April 2025",
                source_fingerprint: "a".repeat(64),
                content_hash: "b".repeat(64),
                overview: {},
                findings: ["Actual observation"],
                recommendations: [],
                investigation_context: [],
              },
              presentation: {
                width: 1000,
                height: 562.5,
                rendering: "Dynamic generated content",
                slides: Array.from({ length: 5 }, (_, i) => ({
                  shapes: [
                    {
                      kind: "text",
                      x: 1,
                      y: 1,
                      width: 500,
                      height: 50,
                      text: `Generated slide ${i + 1}`,
                      font_size: 20,
                    },
                  ],
                })),
              },
            }
          : path.includes("/options")
            ? { options: {} }
            : empty) as never,
    );
    mount(
      <ProductState>
        <Reports />
      </ProductState>,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Continue to evidence" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Review executive brief" }),
    );
    expect(
      await screen.findByRole("img", { name: "Generated slide 1" }),
    ).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Slide 5" }));
    expect(
      screen.getByRole("img", { name: "Generated slide 5" }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Download Presentation" }),
    ).toBeEnabled();
    expect(
      req.mock.calls.find((c) => c[0] === "/reports/preview")?.[2],
    ).toMatchObject({ include_insights: true, include_recommendations: true });
  });
});
