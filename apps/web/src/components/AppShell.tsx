import { useNamespace, setNamespace, usePendingWrites } from "../lib/workspace";
import { useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, lazy, Suspense } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  ChartNoAxesCombined,
  ScanSearch,
  FolderOpen,
  SlidersHorizontal,
  Network,
  Database,
  FileChartColumn,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Sun,
  Moon,
  Menu,
  ArrowUpRight,
} from "lucide-react";
import { Button } from "./ui/button";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetHeader,
  SheetDescription,
} from "./ui/sheet";
const RoutePalette = lazy(() => import("./RoutePalette"));
import { useHealth } from "../hooks/queries";
import { useData } from "../product/shared";
import type { Row } from "../product/shared";
function readStore(store: "localStorage" | "sessionStorage", key: string) {
  try {
    return window[store].getItem(key);
  } catch {
    return null;
  }
}
function writeStore(
  store: "localStorage" | "sessionStorage",
  key: string,
  value: string,
) {
  try {
    window[store].setItem(key, value);
  } catch {
    /* Preferences remain session-local when storage is restricted. */
  }
}
const routes = [
  {
    to: "/",
    label: "Command Center",
    icon: LayoutDashboard,
    group: "Workspace",
  },
  {
    to: "/spend",
    label: "Spend Explorer",
    icon: ChartNoAxesCombined,
    group: "Workspace",
  },
  {
    to: "/investigations/reviews",
    label: "Review Queue",
    icon: ScanSearch,
    group: "Investigations",
  },
  {
    to: "/investigations/cases",
    label: "Saved Cases",
    icon: FolderOpen,
    group: "Investigations",
  },
  {
    to: "/strategy/scenarios",
    label: "Financial Scenarios",
    icon: SlidersHorizontal,
    group: "Strategy Studio",
  },
  {
    to: "/strategy/optimization",
    label: "Optimization",
    icon: Network,
    group: "Strategy Studio",
  },
  {
    to: "/data-operations",
    label: "Data Operations",
    icon: Database,
    group: "Manage",
  },
  { to: "/reports", label: "Reports", icon: FileChartColumn, group: "Manage" },
];
export function AppShell() {
  const location = useLocation();
  const namespace = useNamespace();
  const cache = useQueryClient();
  const mutating = usePendingWrites();
  const health = useHealth();
  const [collapsed, setCollapsed] = useState(
    () => readStore("localStorage", "piq.sidebar") === "collapsed",
  );
  const [mobile, setMobile] = useState(false),
    [command, setCommand] = useState(false);
  const [dark, setDark] = useState(
    () => readStore("localStorage", "piq.theme") === "dark",
  );
  const [lastQueue, setLastQueue] = useState(
    () =>
      readStore("sessionStorage", "procureiq.queueUrl") ||
      "/investigations/reviews",
  );
  const context = useData<{ months: Row[] }>("/command");
  const months = context.data?.months;
  const period = months?.length
    ? `${String(months[0].reporting_month).slice(0, 7)} — ${String(months.at(-1)?.reporting_month).slice(0, 7)}`
    : "HMRC disclosures";
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    writeStore("localStorage", "piq.theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => {
    writeStore(
      "localStorage",
      "piq.sidebar",
      collapsed ? "collapsed" : "expanded",
    );
  }, [collapsed]);
  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommand((s) => !s);
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);
  useEffect(() => {
    if (location.pathname === "/investigations/reviews") {
      const url = location.pathname + location.search;
      setLastQueue(url);
      writeStore("sessionStorage", "procureiq.queueUrl", url);
    }
  }, [location]);
  const current =
    [...routes]
      .reverse()
      .find((r) =>
        r.to === "/"
          ? location.pathname === "/"
          : location.pathname.startsWith(r.to),
      ) || routes[0];
  function navigation() {
    return (
      <nav aria-label="Main navigation">
        {["Workspace", "Investigations", "Strategy Studio", "Manage"].map(
          (group) => (
            <div className="nav-group" key={group}>
              <p>{group}</p>
              {routes
                .filter((r) => r.group === group)
                .map((r) => (
                  <NavLink
                    key={r.to}
                    to={r.to === "/investigations/reviews" ? lastQueue : r.to}
                    end={r.to === "/"}
                    title={r.label}
                    onClick={() => setMobile(false)}
                  >
                    <r.icon size={18} />
                    <span>{r.label}</span>
                  </NavLink>
                ))}
            </div>
          ),
        )}
      </nav>
    );
  }
  const brand = (
    <NavLink to="/" className="piq-brand">
      <span className="piq-mark">
        p<span>q</span>
        <i />
      </span>
      <span>
        ProcureIQ<small>PROCUREMENT INTELLIGENCE</small>
      </span>
    </NavLink>
  );
  return (
    <div className={`product-shell ${collapsed ? "is-collapsed" : ""}`}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="product-sidebar">
        {brand}
        {navigation()}
        <div className="sidebar-end">
          <span className="local-dot" />
          Local workspace<small>Evidence-led decisions.</small>
        </div>
        <Button
          variant="ghost"
          className="collapse-control"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeftOpen size={18} />
          ) : (
            <PanelLeftClose size={18} />
          )}
          <span>Collapse sidebar</span>
        </Button>
      </aside>
      <div className="product-body">
        <header className="product-topbar">
          <Button
            variant="ghost"
            size="icon"
            className="mobile-menu"
            onClick={() => setMobile(true)}
            aria-label="Menu"
          >
            <Menu />
          </Button>
          <div className="workspace-crumb">
            <span>{current.group}</span>
            <span>/</span>
            <strong>{current.label}</strong>
          </div>
          <div className="topbar-tools">
            <span className="period-context">{period}</span>
            <button
              className="command-launch"
              onClick={() => setCommand(true)}
              aria-label="Search routes and actions"
            >
              <Search size={16} />
              <span>Quick jump</span>
              <kbd>⌘ K</kbd>
            </button>
            <span
              className={`connection ${health.isSuccess ? "connected" : ""}`}
              title={
                health.isSuccess
                  ? "Local API connected"
                  : "Local API unavailable"
              }
            >
              <i />
              {health.isSuccess
                ? "Connected"
                : health.isPending
                  ? "Connecting"
                  : "Offline"}
            </span>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setDark(!dark)}
              aria-label={
                dark ? "Switch to light theme" : "Switch to dark theme"
              }
            >
              {dark ? <Sun size={17} /> : <Moon size={17} />}
            </Button>
          </div>
        </header>
        <main id="main" className="workspace-content">
          <div className="workspace-mode-bar">
            <label className="check">
              <input
                type="checkbox"
                checked={namespace === "DEMO"}
                disabled={mutating > 0}
                onChange={async (e) => {
                  const next = e.target.checked ? "DEMO" : "NORMAL";
                  await cache.cancelQueries();
                  cache.clear();
                  setNamespace(next);
                }}
              />
              Demo Mode
            </label>
            <span>
              {namespace === "DEMO"
                ? "Demo workspace · real HMRC evidence, sandbox investigations"
                : "Normal workspace · analyst investigations"}
            </span>
          </div>
          <Outlet />
        </main>
        <footer className="product-footer">
          <span>HMRC published payments · evidence, not inferred savings</span>
          <NavLink to="/data-operations">
            Source integrity <ArrowUpRight size={12} />
          </NavLink>
        </footer>
      </div>
      <Sheet open={mobile} onOpenChange={setMobile}>
        <SheetContent side="left" className="mobile-nav">
          <SheetHeader>
            <SheetTitle>ProcureIQ</SheetTitle>
            <SheetDescription>Your procurement workspace</SheetDescription>
          </SheetHeader>
          {navigation()}
        </SheetContent>
      </Sheet>
      <Suspense fallback={null}>
        {command && (
          <RoutePalette
            routes={routes}
            open={command}
            onOpenChange={setCommand}
          />
        )}
      </Suspense>
    </div>
  );
}
