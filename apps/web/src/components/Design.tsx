import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  FolderSearch,
  ShieldCheck,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Badge } from "./ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "./ui/sheet";
import { Tooltip, TooltipTrigger, TooltipContent } from "./ui/tooltip";
import { money, label, date, score } from "../format";
import { caseTitle, isDemo } from "../lib/presentation";
import type { Case } from "../api/types";
import { StatusBadge } from "./Common";
export function SectionHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}
export function MetricCard({
  label: caption,
  value,
  detail,
  icon,
  accent = false,
}: {
  label: string;
  value: React.ReactNode;
  detail?: string;
  icon?: ReactNode;
  accent?: boolean;
}) {
  return (
    <Card className={`metric-card ${accent ? "metric-accent" : ""}`}>
      <div className="metric-top">
        <span>{caption}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </Card>
  );
}
export function Panel({
  title,
  action,
  children,
  className = "",
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader className="panel-heading">
        <CardTitle>{title}</CardTitle>
        {action}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
export function DetailDrawer({
  title,
  description,
  children,
  onClose,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <Sheet
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <SheetContent className="detail-drawer">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>
            {description || "Review the record and its supporting evidence."}
          </SheetDescription>
        </SheetHeader>
        <div className="drawer-body">{children}</div>
      </SheetContent>
    </Sheet>
  );
}
export function Hint({
  text,
  children,
}: {
  text: string;
  children: ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0}>{children}</span>
      </TooltipTrigger>
      <TooltipContent>{text}</TooltipContent>
    </Tooltip>
  );
}
export function EmptyState({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <FolderSearch size={26} />
      </span>
      <h3>{title}</h3>
      <p>{detail}</p>
      {action}
    </div>
  );
}
export function CaseCard({ record: c }: { record: Case }) {
  return (
    <Link className="case-card" to={`/investigations/cases/${c.case_id}`}>
      <div className="case-card-top">
        <span className="eyebrow">{c.case_reference}</span>
        <div>
          {isDemo(c) && <Badge variant="outline">Demo</Badge>}{" "}
          <StatusBadge status={c.status} />
        </div>
      </div>
      <h3>{caseTitle(c)}</h3>
      <p>{label(c.opportunity_type)}</p>
      <div className="case-card-meta">
        <span>{c.primary_count.toLocaleString()} records</span>
        <span>Priority {score(c.original_score)}</span>
      </div>
      <div className="case-card-bottom">
        <small>
          <ShieldCheck size={13} />
          {c.basis_matches_current_source
            ? "Current source"
            : "Historical source"}
        </small>
        <span>
          Continue <ArrowRight size={15} />
        </span>
      </div>
      <small className="muted">Updated {date(c.updated_at)}</small>
    </Link>
  );
}
export function ExactMoney({ value }: { value: string }) {
  return (
    <Hint text={money(value)}>
      <span className="tabular-nums">{money(value)}</span>
    </Hint>
  );
}
export function ActionLink({
  to,
  children,
}: {
  to: string;
  children: ReactNode;
}) {
  return (
    <Link className="text-action" to={to}>
      {children}
      <ArrowUpRight size={15} />
    </Link>
  );
}
