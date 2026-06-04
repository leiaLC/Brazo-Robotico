"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type PowerTrendPoint = {
  time: string;
  watts: number;
};

export function PowerUsageChart({ data }: { data: PowerTrendPoint[] }) {
  const maxWatts = Math.max(10, ...data.map((item) => item.watts));

  return (
    <div className="industrial-scrollbar w-full overflow-x-auto">
      <BarChart
        className="max-w-full"
        data={data}
        height={420}
        margin={{ top: 20, right: 18, left: 0, bottom: 10 }}
        width={1040}
      >
          <CartesianGrid stroke="#E1E5EA" vertical={false} />
          <XAxis
            axisLine={false}
            dataKey="time"
            tick={{ fill: "#828A95", fontSize: 13 }}
            tickLine={false}
          />
          <YAxis
            axisLine={false}
            domain={[0, Math.ceil(maxWatts + 2)]}
            tick={{ fill: "#828A95", fontSize: 13 }}
            tickLine={false}
            unit=" W"
          />
          <Tooltip
            contentStyle={{
              border: "1px solid #C2CAD6",
              borderRadius: 8,
              boxShadow: "0 8px 20px rgba(20,30,45,0.12)",
            }}
            cursor={{ fill: "#EDF3FA" }}
          />
          <Bar dataKey="watts" fill="#5D89A5" name="Power" radius={[3, 3, 0, 0]} unit=" W" />
        </BarChart>
    </div>
  );
}
