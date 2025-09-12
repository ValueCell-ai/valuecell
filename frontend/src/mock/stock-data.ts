import type { StockGroup } from "@/components/menus/stock-menus";

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
    ],
  },
  {
    title: "A-Share",
    stocks: [
      {
        symbol: "MAOTAI",
        companyName: "Maotai, Inc",
        price: 88.91,
        currency: "¥",
        changePercent: 1.29,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "BYD",
        companyName: "BYD, Inc",
        price: 142.65,
        currency: "¥",
        changePercent: 0.81,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
      {
        symbol: "BOC",
        companyName: "Bank of China, Inc",
        price: 142.65,
        currency: "¥",
        changePercent: 0.81,
        icon: undefined,
        iconBgColor: "#EEF0F3",
      },
    ],
  },
];
