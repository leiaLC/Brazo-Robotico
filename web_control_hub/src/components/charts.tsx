"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { energyTrend } from "@/lib/mock-data";

export function EnergyUsageChart() {
  return (
    <div className="industrial-scrollbar w-full overflow-x-auto">
      <BarChart
        className="max-w-full"
        data={energyTrend}
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
            domain={[0, 5]}
            tick={{ fill: "#828A95", fontSize: 13 }}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              border: "1px solid #C2CAD6",
              borderRadius: 8,
              boxShadow: "0 8px 20px rgba(20,30,45,0.12)",
            }}
            cursor={{ fill: "#EDF3FA" }}
          />
          <Bar dataKey="energy" fill="#5D89A5" radius={[3, 3, 0, 0]} />
        </BarChart>
    </div>
  );
}
