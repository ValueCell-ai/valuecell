import type { SparklineStock } from "@/app/home/components/sparkline-stock-list";
import type { StockGroup } from "@/components/valuecell/menus/stock-menus";
import { nowUTC, subtract } from "@/lib/time";
import type { SparklineData } from "@/types/chart";

export const stockData: StockGroup[] = [
  {
    title: "US shares",
    stocks: [
      {
        symbol: "NFLX",
        companyName: "Netflix, Inc",
        price: 88.91,
        currency: "$",
        changePercent: 1.29,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "AAPL",
        companyName: "Apple, Inc",
        price: 142.65,
        currency: "$",
        changePercent: 0.81,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "BAC",
        companyName: "Bank of America",
        price: 43.08,
        currency: "$",
        changePercent: 0.3,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "TSLA",
        companyName: "Tesla, Inc",
        price: 251.44,
        currency: "$",
        changePercent: -2.15,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "GOOGL",
        companyName: "Alphabet Inc",
        price: 138.21,
        currency: "$",
        changePercent: 0.92,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "MSFT",
        companyName: "Microsoft Corporation",
        price: 376.04,
        currency: "$",
        changePercent: 1.47,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "AMZN",
        companyName: "Amazon.com, Inc",
        price: 134.95,
        currency: "$",
        changePercent: -0.73,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "META",
        companyName: "Meta Platforms, Inc",
        price: 298.58,
        currency: "$",
        changePercent: 2.18,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
    ],
  },
  {
    title: "A-Share",
    stocks: [
      {
        symbol: "MAOTAI",
        companyName: "Kweichow Moutai Co",
        price: 1678.5,
        currency: "¥",
        changePercent: 1.29,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "BYD",
        companyName: "BYD Company Ltd",
        price: 228.75,
        currency: "¥",
        changePercent: 0.81,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "BOC",
        companyName: "Bank of China Ltd",
        price: 3.54,
        currency: "¥",
        changePercent: -0.28,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "PING AN",
        companyName: "Ping An Insurance",
        price: 45.67,
        currency: "¥",
        changePercent: 1.85,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "TENCENT",
        companyName: "Tencent Holdings",
        price: 342.8,
        currency: "¥",
        changePercent: -1.42,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "ALIBABA",
        companyName: "Alibaba Group",
        price: 78.95,
        currency: "¥",
        changePercent: 3.21,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
    ],
  },
  {
    title: "Crypto",
    stocks: [
      {
        symbol: "BTC",
        companyName: "Bitcoin",
        price: 43256.78,
        currency: "$",
        changePercent: 2.34,
        icon: undefined,
        iconBgColor: "#F7931A",
      },
      {
        symbol: "ETH",
        companyName: "Ethereum",
        price: 2587.44,
        currency: "$",
        changePercent: 1.87,
        icon: undefined,
        iconBgColor: "#627EEA",
      },
      {
        symbol: "BNB",
        companyName: "Binance Coin",
        price: 312.45,
        currency: "$",
        changePercent: -0.95,
        icon: undefined,
        iconBgColor: "#F3BA2F",
      },
    ],
  },
];

// Generate random sparkline data in [utctime, value] format
function generateSparklineData(): SparklineData {
  const data: SparklineData = [];
  const startValue = 100 + Math.random() * 50; // start value between 100-150
  let value = startValue;
  const currentTime = nowUTC();

  // Add some overall trend bias (slightly bearish to bullish)
  const trendBias = (Math.random() - 0.5) * 0.002; // -0.1% to +0.1% per step

  for (let i = 0; i < 30; i++) {
    // Generate time points going backwards from current time (each point is 30 minutes apart)
    const timePoint = subtract(currentTime, (29 - i) * 30, "minute").valueOf();

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
