import { useNamespace } from "./lib/workspace";
import { lazy, Suspense } from "react";
import { Loading } from "./components/Common";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Command } from "./product/Command";
import { Spend, Supplier } from "./product/Spend";
import { Scenarios, ProductState } from "./product/Strategy";
const Optimization = lazy(() =>
  import("./product/Optimization").then((m) => ({ default: m.Optimization })),
);
const Operations = lazy(() =>
  import("./product/Operations").then((m) => ({ default: m.Operations })),
);
const PipelineRun = lazy(() =>
  import("./product/Operations").then((m) => ({ default: m.PipelineRun })),
);
const Reports = lazy(() =>
  import("./product/Reports").then((m) => ({ default: m.Reports })),
);
import { AppShell } from "./components/AppShell";
import { TooltipProvider } from "./components/ui/tooltip";
import { Toaster } from "sonner";
import { NavLink, Route, Routes } from "react-router-dom";

import { ReviewQueue } from "./pages/ReviewQueue";
import { Cases } from "./pages/Cases";
import { CaseWorkspace } from "./pages/CaseWorkspace";
export function App() {
  const namespace = useNamespace();
  return (
    <ErrorBoundary>
      <TooltipProvider delayDuration={250}>
        <ProductState key={namespace}>
          <Suspense fallback={<Loading />}>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<Command />} />
                <Route path="spend" element={<Spend />} />
                <Route
                  path="spend/suppliers/:supplierId"
                  element={<Supplier />}
                />
                <Route path="strategy/scenarios" element={<Scenarios />} />
                <Route
                  path="strategy/optimization"
                  element={<Optimization />}
                />
                <Route path="data-operations" element={<Operations />} />
                <Route
                  path="data-operations/runs/:runId"
                  element={<PipelineRun />}
                />
                <Route path="reports" element={<Reports />} />
                <Route
                  path="investigations/reviews"
                  element={<ReviewQueue />}
                />
                <Route path="investigations/cases" element={<Cases />} />
                <Route
                  path="investigations/cases/:caseId"
                  element={<CaseWorkspace />}
                />
                <Route
                  path="*"
                  element={
                    <div className="empty">
                      <h1>Page not found</h1>
                      <NavLink to="/investigations/reviews">
                        Open Review Queue
                      </NavLink>
                    </div>
                  }
                />
              </Route>
            </Routes>
          </Suspense>
        </ProductState>
        <Toaster
          richColors
          position="bottom-right"
          toastOptions={{
            style: {
              background: "var(--card)",
              color: "var(--foreground)",
              border: "1px solid var(--border)",
            },
          }}
        />
      </TooltipProvider>
    </ErrorBoundary>
  );
}
