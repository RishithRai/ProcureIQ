import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  LineChart,
  Line,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { label, money } from "../format";
import type { Row } from "./shared";
export default function Chart({
  rows,
  x,
  value,
  line = false,
  onSelect,
  compare,
}: {
  rows: Row[];
  x: string;
  value: string;
  line?: boolean;
  onSelect?: (row: Row) => void;
  compare?: string;
}) {
  const data = rows.map((r) => ({
    ...r,
    [value]: Number(r[value]),
    ...(compare ? { [compare]: Number(r[compare]) } : {}),
  }));
  return (
    <div className="chart" aria-label={`${label(value)} chart`}>
      <ResponsiveContainer width="100%" height={250}>
        {line ? (
          <LineChart
            data={data}
            onClick={(state) => {
              const i = Number(state.activeTooltipIndex);
              if (onSelect && Number.isInteger(i) && rows[i]) onSelect(rows[i]);
            }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="var(--border)"
            />
            <XAxis
              dataKey={x}
              tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
            />
            <YAxis
              width={65}
              tickFormatter={(v: number) =>
                Math.abs(v) >= 1000000
                  ? `${(v / 1000000).toFixed(1).replace(/\.0$/, "")}m`
                  : Math.abs(v) >= 1000
                    ? `${(v / 1000).toFixed(1).replace(/\.0$/, "")}k`
                    : String(v)
              }
              tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
            />
            <Tooltip
              formatter={(v) =>
                value.endsWith("gbp") ? money(String(v)) : String(v)
              }
              contentStyle={{
                background: "var(--card)",
                color: "var(--foreground)",
                border: "1px solid var(--border)",
                borderRadius: 8,
              }}
            />
            {value === "cumulative_resolved_pct" && (
              <ReferenceLine
                y={80}
                label="80% of resolved positive payments"
                stroke="var(--muted-foreground)"
                strokeDasharray="4 4"
              />
            )}
            <Line
              isAnimationActive={false}
              dataKey={value}
              name={label(value)}
              stroke="var(--primary)"
              strokeWidth={2.5}
              dot={false}
            />
          </LineChart>
        ) : (
          <BarChart
            data={data}
            onClick={(state) => {
              const i = Number(state.activeTooltipIndex);
              if (onSelect && Number.isInteger(i) && rows[i]) onSelect(rows[i]);
            }}
          >
            <XAxis
              dataKey={x}
              tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
              hide={data.length > 12}
            />
            <YAxis
              width={65}
              tickFormatter={(v: number) =>
                Math.abs(v) >= 1000000
                  ? `${(v / 1000000).toFixed(1).replace(/\.0$/, "")}m`
                  : Math.abs(v) >= 1000
                    ? `${(v / 1000).toFixed(1).replace(/\.0$/, "")}k`
                    : String(v)
              }
              tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
            />
            <Tooltip
              formatter={(v) =>
                value.endsWith("gbp") ? money(String(v)) : String(v)
              }
              contentStyle={{
                background: "var(--card)",
                color: "var(--foreground)",
                border: "1px solid var(--border)",
                borderRadius: 8,
              }}
            />
            {compare && (
              <Bar
                isAnimationActive={false}
                dataKey={compare}
                name={label(compare)}
                fill="var(--chart-2)"
                radius={[6, 6, 0, 0]}
              />
            )}
            <Bar
              isAnimationActive={false}
              dataKey={value}
              name={label(value)}
              fill="var(--primary)"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        )}
      </ResponsiveContainer>
      <small className="muted">
        Chart scale is illustrative display precision; exact API values remain
        in tables.
      </small>
    </div>
  );
}
