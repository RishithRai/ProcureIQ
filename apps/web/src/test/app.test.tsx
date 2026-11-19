import * as clientModule from "../api/client";
import { getNamespace } from "../lib/workspace";
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "../App";
import { api, ApiError, request } from "../api/client";
import { caseTitle } from "../lib/presentation";
import { money } from "../format";
import { parseQueue } from "../hooks/queue";
import reviewFixture from "./review.json";
import caseFixture from "./case.json";
import evidenceFixture from "./evidence.json";
import activityFixture from "./activity.json";
import type { Reviews, Case, EvidencePage, Page, Event } from "../api/types";
const reviews = reviewFixture as Reviews,
  saved = { ...caseFixture, namespace: "NORMAL" } as Case;
function mocks() {
  vi.spyOn(clientModule, "request").mockImplementation(async (path, signal) => {
    const u = new URL("http://local" + path);
    const id = u.pathname.split("/")[3];
    if (path.includes("/evidence?"))
      return (await api.evidence(
        id,
        u.searchParams.get("classification") || "primary",
        Number(u.searchParams.get("offset") || 0),
        signal,
      )) as never;
    if (path.includes("/activity?"))
      return (await api.activity(
        id,
        Number(u.searchParams.get("offset") || 0),
        signal,
      )) as never;
    return { items: [], total: 0, offset: 0, limit: 50 } as never;
  });

  vi.spyOn(api, "health").mockResolvedValue({ status: "ok" });
  vi.spyOn(api, "reviews").mockResolvedValue(structuredClone(reviews));
  vi.spyOn(api, "review").mockResolvedValue(structuredClone(reviews));
  vi.spyOn(api, "case").mockResolvedValue(structuredClone(saved));
  vi.spyOn(api, "cases").mockResolvedValue({
    items: [saved],
    total: 1,
    offset: 0,
    limit: 50,
  });
  vi.spyOn(api, "evidence").mockResolvedValue(evidenceFixture as EvidencePage);
  vi.spyOn(api, "activity").mockResolvedValue(
    activityFixture as unknown as Page<Event>,
  );
}
function app(path = "/investigations/reviews") {
  const q = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={q}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
async function select() {
  await userEvent.click(
    await screen.findByRole("button", { name: /Priority 97.95/ }),
  );
  await screen.findByRole("heading", { name: "Observed Evidence" });
}
function newReview() {
  const r = structuredClone(reviews);
  delete r.items[0].existing_case;
  vi.mocked(api.reviews).mockResolvedValue(r);
  vi.mocked(api.review).mockResolvedValue(r);
  return r;
}
describe("Investigation workspace", () => {
  it("renders the actual-shaped queue, selects and opens an existing case", async () => {
    mocks();
    app();
    await select();
    expect(screen.getAllByText("£721,458,382.18").length).toBeGreaterThan(0);
    await userEvent.click(
      screen.getByRole("link", { name: "Open Investigation" }),
    );
    expect(
      await screen.findByRole("heading", { name: caseTitle(saved) }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Investigating").length).toBeGreaterThan(0);
  });
  it("uses exact single filters, resets, and preserves display-only creation eligibility", async () => {
    mocks();
    app();
    await screen.findByRole("heading", { name: "Review Queue" });
    await userEvent.click(screen.getByText("Reporting & review filters"));
    await userEvent.type(
      screen.getByLabelText("Expense Type"),
      " PROJECT Mandays Supp ",
    );
    await userEvent.selectOptions(
      screen.getByLabelText("Detector type"),
      "purchasing_fragmentation",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Apply filters" }),
    );
    await waitFor(() =>
      expect(api.reviews).toHaveBeenLastCalledWith(
        expect.stringContaining("expense_type=+PROJECT+Mandays+Supp+"),
        expect.any(AbortSignal),
      ),
    );
    await userEvent.click(screen.getByText("Reporting & review filters"));
    await userEvent.click(
      screen.getByRole("button", { name: "Reset Filters" }),
    );
    await waitFor(() =>
      expect(api.reviews).toHaveBeenLastCalledWith(
        "&offset=0&limit=50",
        expect.any(AbortSignal),
      ),
    );
  });
  it("searches only the loaded page and handles empty reviews", async () => {
    mocks();
    app();
    await screen.findByRole("button", { name: /Priority/ });
    await userEvent.type(
      screen.getByLabelText("Search loaded reviews"),
      "no-such-review",
    );
    expect(await screen.findByText("No matching reviews")).toBeInTheDocument();
    expect(screen.getByText(/Search applies to this page/)).toBeInTheDocument();
  });
  it("validates creation, sends only authoritative context identifiers and navigates on success", async () => {
    mocks();
    const r = newReview();
    const create = vi
      .spyOn(api, "create")
      .mockResolvedValue({ created: true, case: saved });
    app();
    await select();
    await userEvent.click(
      screen.getByRole("button", { name: "Create Investigation" }),
    );
    const dialog = screen.getByRole("dialog");
    await userEvent.clear(
      within(dialog).getByLabelText("Investigation objective"),
    );
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Create Investigation" }),
    );
    expect(create).not.toHaveBeenCalled();
    expect(within(dialog).getByRole("alert")).toHaveTextContent(
      "meaningful objective",
    );
    await userEvent.type(
      within(dialog).getByLabelText("Investigation objective"),
      "Inspect the immutable source evidence.",
    );
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Create Investigation" }),
    );
    expect(
      await screen.findByText(
        "Investigation created with its original evidence basis.",
      ),
    ).toBeInTheDocument();
    expect(create).toHaveBeenCalledWith({
      review_id: r.items[0].opportunity_id,
      basis_token: r.basis_token,
      filters: r.basis.filters,
      title: r.items[0].title,
      objective: "Inspect the immutable source evidence.",
    });
  });
  it("reports concurrent existing result truthfully", async () => {
    mocks();
    newReview();
    vi.spyOn(api, "create").mockResolvedValue({ created: false, case: saved });
    app();
    await select();
    await userEvent.click(
      screen.getByRole("button", { name: "Create Investigation" }),
    );
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Create Investigation",
      }),
    );
    expect(
      await screen.findByText(/already exists for this exact/),
    ).toBeInTheDocument();
  });
  it("refreshes stale basis without silently retrying a write", async () => {
    mocks();
    newReview();
    const create = vi
      .spyOn(api, "create")
      .mockRejectedValue(new ApiError("stale_review_basis"));
    app();
    await select();
    await userEvent.click(
      screen.getByRole("button", { name: "Create Investigation" }),
    );
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Create Investigation",
      }),
    );
    expect(
      await screen.findByText(/nothing was submitted again automatically/),
    ).toBeInTheDocument();
    expect(create).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(api.review).toHaveBeenCalledTimes(2));
  });
  it("keeps closed cases read-only and never calls creation on open", async () => {
    mocks();
    const r = structuredClone(reviews);
    r.items[0].existing_case!.status = "CLOSED";
    vi.mocked(api.review).mockResolvedValue(r);
    vi.mocked(api.case).mockResolvedValue({ ...saved, status: "CLOSED" });
    const create = vi.spyOn(api, "create");
    app();
    await select();
    await userEvent.click(
      screen.getByRole("link", { name: "View Closed Investigation" }),
    );
    expect(
      await screen.findByRole("button", { name: "Manage case lifecycle" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /close case|edit status/i }),
    ).not.toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });
  it("supports saved-case filtering and navigation", async () => {
    mocks();
    app("/investigations/cases");
    await userEvent.selectOptions(
      screen.getByLabelText("Status"),
      "INVESTIGATING",
    );
    await waitFor(() =>
      expect(api.cases).toHaveBeenLastCalledWith(
        "offset=0&limit=50&status=INVESTIGATING",
        expect.any(AbortSignal),
      ),
    );

    await userEvent.click(
      await screen.findByRole("link", {
        name: new RegExp(saved.case_reference),
      }),
    );
    expect(
      await screen.findByRole("heading", { name: caseTitle(saved) }),
    ).toBeInTheDocument();
  });
  it("renders a meaningful empty saved-case population", async () => {
    mocks();
    vi.mocked(api.cases).mockResolvedValue({
      items: [],
      total: 0,
      offset: 0,
      limit: 50,
    });
    app("/investigations/cases");
    expect(
      await screen.findByText("No cases in this view"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Browse the Review Queue" }),
    ).toBeInTheDocument();
  });
  it("loads only requested evidence pages and resets classification pagination", async () => {
    mocks();
    app("/investigations/cases/1?tab=evidence");
    await screen.findByRole("table");
    expect(api.evidence).toHaveBeenCalledWith(
      "1",
      "primary",
      0,
      expect.any(AbortSignal),
    );
    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    await waitFor(() =>
      expect(api.evidence).toHaveBeenLastCalledWith(
        "1",
        "primary",
        50,
        expect.any(AbortSignal),
      ),
    );
    await userEvent.selectOptions(
      screen.getByLabelText("Evidence classification"),
      "contextual",
    );
    await waitFor(() =>
      expect(api.evidence).toHaveBeenLastCalledWith(
        "1",
        "contextual",
        0,
        expect.any(AbortSignal),
      ),
    );
    await userEvent.click(
      (
        await screen.findAllByRole("button", { name: /Inspect source record/ })
      )[0],
    );
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByText(evidenceFixture.items[0].file_sha256),
    ).toBeInTheDocument();
  });
  it("shows activity in backend order with the real application actor", async () => {
    mocks();
    app("/investigations/cases/1?tab=activity");
    expect(
      await screen.findByRole("heading", { name: "Case Created" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Status Changed" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Local application · Event/)).toHaveLength(2);
    const heads = screen.getAllByRole("heading", { level: 3 });
    expect(heads.map((h) => h.textContent)).toEqual([
      "Case Created",
      "Status Changed",
    ]);
  });
  it("shows historical source notice and integrity failure as error, not an empty table", async () => {
    mocks();
    vi.mocked(api.case).mockResolvedValue({
      ...saved,
      basis_matches_current_source: false,
    });
    vi.mocked(api.evidence).mockRejectedValue(
      new ApiError("evidence_integrity"),
    );
    app("/investigations/cases/1?tab=evidence");
    expect(
      (await screen.findAllByText("Historical Evidence Basis")).length,
    ).toBeGreaterThan(0);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "integrity check failed",
    );
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
  it("offers retry when API is offline, with no mock substitution", async () => {
    mocks();
    vi.mocked(api.reviews).mockRejectedValueOnce(new ApiError("offline"));
    app();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Cannot reach the local API",
    );
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByRole("button", { name: /Priority/ }),
    ).toBeInTheDocument();
  });
  it("has keyboard-accessible queue controls", async () => {
    mocks();
    app();
    await screen.findByRole("button", { name: /Priority/ });
    await userEvent.tab();
    expect(screen.getByText("Skip to content")).toHaveFocus();
    screen.getByRole("button", { name: /Priority/ }).focus();
    await userEvent.keyboard("{Enter}");
    expect(
      await screen.findByRole("heading", { name: "Observed Evidence" }),
    ).toBeInTheDocument();
  });
  it("rejects invalid restored URL filters before API retrieval", async () => {
    mocks();
    app("/investigations/reviews?supplier_id=-1");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid URL filters",
    );
    expect(api.reviews).not.toHaveBeenCalled();
  });
});
describe("navigation and request isolation", () => {
  it("preserves queue selection and search through saved-case navigation", async () => {
    mocks();
    app();
    await select();
    await userEvent.type(
      screen.getByLabelText("Search loaded reviews"),
      "Mandays",
    );
    await userEvent.click(
      screen.getByRole("link", { name: "Open Investigation" }),
    );
    await screen.findByRole("heading", { name: caseTitle(saved) });
    await userEvent.click(screen.getByRole("link", { name: "Review Queue" }));
    expect(await screen.findByLabelText("Search loaded reviews")).toHaveValue(
      "Mandays",
    );
    expect(
      await screen.findByRole("link", { name: "Open Investigation" }),
    ).toBeInTheDocument();
  });
  it("ignores an older response after filters change", async () => {
    mocks();
    let finish!: (r: Reviews) => void;
    vi.mocked(api.reviews).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    app();
    await screen.findByRole("heading", { name: "Review Queue" });
    await userEvent.click(screen.getByText("Reporting & review filters"));
    await userEvent.type(screen.getByLabelText("Expense Area"), "CDIO - Core");
    await userEvent.click(
      screen.getByRole("button", { name: "Apply filters" }),
    );
    await screen.findByRole("button", { name: /Priority/ });
    const old = structuredClone(reviews);
    old.items[0].title = "Obsolete response";
    finish(old);
    await waitFor(() =>
      expect(screen.queryByText("Obsolete response")).not.toBeInTheDocument(),
    );
    expect(vi.mocked(api.reviews).mock.calls[0][1]?.aborted).toBe(true);
  });
  it("shows an empty contextual evidence population without reading other pages", async () => {
    mocks();
    vi.mocked(api.evidence).mockResolvedValue({
      ...evidenceFixture,
      items: [],
      total: 0,
      classification: "contextual",
    } as EvidencePage);
    app("/investigations/cases/1?tab=evidence");
    await userEvent.selectOptions(
      await screen.findByLabelText("Evidence classification"),
      "contextual",
    );
    expect(
      await screen.findByText(
        "No matching evidence. Adjust or reset your filters.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
  });
});

describe("boundary conventions", () => {
  it("formats exact money without binary conversion, including beyond safe integers", () => {
    expect(money("721458382.18")).toBe("£721,458,382.18");
    expect(money("9007199254740993.01")).toBe("£9,007,199,254,740,993.01");
    expect(money("-0.01")).toBe("-£0.01");
    expect(money("0")).toBe("£0.00");
  });
  it("keeps canonical scope separate from display filters and validates dates", () => {
    const x = parseQueue(
      new URLSearchParams(
        "expense_type=+Exact+&minimum_priority=30&detector_type=data_quality",
      ),
    );
    expect(x.reporting).toBe("expense_type=+Exact+");
    expect(x.invalid).toBe(false);
    expect(parseQueue(new URLSearchParams("start_month=2025-13")).invalid).toBe(
      true,
    );
    expect(
      parseQueue(new URLSearchParams("start_month=2026-01&end_month=2025-01"))
        .invalid,
    ).toBe(true);
  });
  it("decodes the exact structured error and forwards cancellation", async () => {
    const ctrl = new AbortController();
    const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "stale_review_basis", message: "sanitized" },
        }),
        { status: 409 },
      ),
    );
    await expect(request("/test", ctrl.signal)).rejects.toMatchObject({
      code: "stale_review_basis",
    });
    expect(fetcher).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ signal: ctrl.signal }),
    );
  });
});

describe("Redesigned navigation and preserved demo records", () => {
  it("opens the route palette by keyboard, filters destinations and navigates", async () => {
    mocks();
    app();
    await screen.findByRole("button", { name: /Priority/ });
    await userEvent.keyboard("{Control>}k{/Control}");
    expect(
      await screen.findByRole("dialog", { name: "Go to workspace" }),
    ).toBeInTheDocument();
    await userEvent.type(
      screen.getByPlaceholderText("Where would you like to go?"),
      "Saved Cases",
    );
    await userEvent.keyboard("{Enter}");
    expect(
      await screen.findByRole("heading", { name: "Saved cases" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it("switches explicit persisted namespaces and preserves original demo wording", async () => {
    mocks();
    const demo = { ...saved, namespace: "DEMO" as const };
    const normal = {
      ...saved,
      namespace: "NORMAL" as const,
      case_id: 77,
      case_reference: "PIQ-000077",
      title: "Supplier exposure investigation",
    };
    vi.mocked(api.cases).mockImplementation(async () => ({
      items: [getNamespace() === "DEMO" ? demo : normal],
      total: 1,
      offset: 0,
      limit: 50,
    }));
    vi.mocked(api.case).mockResolvedValue(demo);
    app("/investigations/cases");
    expect(
      await screen.findByRole("link", { name: /PIQ-000077/ }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /PIQ-000001/ }),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByLabelText("Demo Mode"));
    await userEvent.click(
      await screen.findByRole("link", { name: /PIQ-000001/ }),
    );
    await screen.findByRole("heading", { name: caseTitle(demo) });
    await userEvent.click(screen.getByText("Original saved title"));
    expect(screen.getByText(saved.title)).toBeVisible();
    expect(screen.getByText(saved.objective)).toBeVisible();
  });
  it("switches themes and collapses the sidebar without losing accessible navigation", async () => {
    mocks();
    app();
    await screen.findByRole("button", { name: /Priority/ });
    await userEvent.click(
      screen.getByRole("button", { name: "Switch to dark theme" }),
    );
    expect(document.documentElement).toHaveClass("dark");
    await userEvent.click(
      screen.getByRole("button", { name: "Collapse sidebar" }),
    );
    expect(localStorage.getItem("piq.sidebar")).toBe("collapsed");
    expect(
      screen.getByRole("link", { name: "Spend Explorer" }),
    ).toHaveAttribute("href", "/spend");
    await userEvent.click(
      screen.getByRole("button", { name: "Switch to light theme" }),
    );
    expect(document.documentElement).not.toHaveClass("dark");
  });
  it("opens lifecycle confirmation without mutating a case and supports Escape", async () => {
    mocks();
    app("/investigations/cases/1");
    await screen.findByRole("heading", { name: caseTitle(saved) });
    await userEvent.click(
      screen.getByRole("button", { name: "Manage case lifecycle" }),
    );
    const dialog = screen.getByRole("dialog", { name: "Move to reviewed" });
    expect(within(dialog).getByLabelText("Written reason")).toBeVisible();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
