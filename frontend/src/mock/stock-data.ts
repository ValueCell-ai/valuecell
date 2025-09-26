import type { SparklineStock } from "@/app/home/components/sparkline-stock-list";
import { TimeUtils } from "@/lib/time";
import type { SparklineData } from "@/types/chart";

// Generate random sparkline data in [utctime, value] format
function generateSparklineData(): SparklineData {
  const data: SparklineData = [];
  const startValue = 100 + Math.random() * 50; // start value between 100-150
  let value = startValue;
  const currentTime = TimeUtils.nowUTC();

  // Add some overall trend bias (slightly bearish to bullish)
  const trendBias = (Math.random() - 0.5) * 0.002; // -0.1% to +0.1% per step

  for (let i = 0; i < 30; i++) {
    // Generate time points going backwards from current time (each point is 30 minutes apart)
    const timePoint = TimeUtils.subtract(
      currentTime,
      (29 - i) * 30,
      "minute",
    ).valueOf();

    // Random walk with trend bias
    const randomChange = (Math.random() - 0.5) * 0.06; // -3% to +3% random
    const changePercent = randomChange + trendBias;

    // Apply change
    value = value * (1 + changePercent);

    // Prevent negative values and extreme deviations
    value = Math.max(value, startValue * 0.3); // Don't go below 30% of start
    value = Math.min(value, startValue * 3); // Don't go above 300% of start

    data.push([timePoint, Number(value.toFixed(2))]);
  }

  return data;
}

export const sparklineStockData: SparklineStock[] = [
  {
    symbol: "DJI",
    price: 38808.72,
    currency: "$",
    changeAmount: 66.84,
    changePercent: 1.75,
    sparklineData: generateSparklineData(),
  },
  {
    symbol: "IXIC",
    price: 12063.17,
    currency: "$",
    changeAmount: -66.84,
    changePercent: -1.75,
    sparklineData: generateSparklineData(),
  },
  {
    symbol: "SPX",
    price: 2770.94,
    currency: "$",
    changeAmount: -128.43,
    changePercent: -4.43,
    sparklineData: generateSparklineData(),
  },
];
