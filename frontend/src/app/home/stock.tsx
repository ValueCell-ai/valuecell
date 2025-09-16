import BackButton from "@valuecell/button/back-button";
import Sparkline from "@valuecell/charts/sparkline";
import { StockIcon } from "@valuecell/menus/stock-menus";
import { memo, useCallback, useMemo } from "react";
import { useParams } from "react-router";
import { StockDetailsList } from "@/app/home/components";
import { Button } from "@/components/ui/button";
import { stockData } from "@/mock/stock-data";

// 生成历史价格数据
function generateHistoricalData(basePrice: number, days: number = 30) {
  const data = [];
  const now = new Date();

  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);

    // 模拟价格波动 (±5%)
    const variation = (Math.random() - 0.5) * 0.1;
    const price = basePrice * (1 + variation * (i / days)); // 添加趋势

    data.push({
      timestamp: date.toISOString(),
      value: Math.max(0, price),
    });
  }

  return data;
}

const Stock = memo(function Stock() {
  const { stockId } = useParams();

  // 从 mock 数据中查找股票信息
  const stockInfo = useMemo(() => {
    for (const group of stockData) {
      const stock = group.stocks.find((s) => s.symbol === stockId);
      if (stock) return stock;
    }
    return null;
  }, [stockId]);

  // 生成60天历史数据（固定，按设计）
  const chartData = useMemo(() => {
    if (!stockInfo) return [];
    return generateHistoricalData(stockInfo.price, 60);
  }, [stockInfo]);

  // 生成模拟的详细数据（按Figma设计）
  const detailsData = useMemo(() => {
    if (!stockInfo) return undefined;

    const basePrice = stockInfo.price;
    const previousClose = basePrice * (0.99 + Math.random() * 0.02);
    const dayLow = basePrice * (0.95 + Math.random() * 0.05);
    const dayHigh = basePrice * (1.01 + Math.random() * 0.04);
    const yearLow = basePrice * (0.6 + Math.random() * 0.2);
    const yearHigh = basePrice * (1.1 + Math.random() * 0.3);

    return {
      previousClose: previousClose.toFixed(2),
      dayRange: `${dayLow.toFixed(2)} - ${dayHigh.toFixed(2)}`,
      yearRange: `${yearLow.toFixed(2)} - ${yearHigh.toFixed(2)}`,
      marketCap: `$${(Math.random() * 50 + 10).toFixed(1)} T USD`,
      volume: `${(Math.random() * 5000000 + 1000000).toLocaleString()}`,
      dividendYield: `${(Math.random() * 3 + 0.5).toFixed(2)}%`,
    };
  }, [stockInfo]);

  const formatTooltip = useCallback(
    (value: number, timestamp: string) => {
      if (!stockInfo) return "";

      const date = new Date(timestamp);
      const formatDate = date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      const formatTime = date.toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
      });

      return `
        <div style="font-weight: 500; font-size: 12px; margin-bottom: 8px; letter-spacing: -3.5%;">
          ${formatDate}, ${formatTime}
        </div>
        <div style="font-weight: bold; font-size: 18px; font-family: 'SF Pro Display', sans-serif;">
          ${value.toFixed(2)}
        </div>
      `;
    },
    [stockInfo],
  );

  if (!stockInfo) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-gray-500 text-lg">未找到股票 {stockId}</div>
      </div>
    );
  }

  const isPositive = stockInfo.changePercent >= 0;
  const chartColor = "#41C3A9"; // 固定为设计中的绿色
  const gradientColors: [string, string] = [
    "rgba(65, 195, 169, 0.6)",
    "rgba(65, 195, 169, 0)",
  ];

  return (
    <div className="flex flex-col gap-8 px-8 py-6">
      {/* Stock Main Info */}
      <div className="flex flex-col gap-4">
        <BackButton />

        <div className="flex items-center gap-2">
          <StockIcon stock={stockInfo} />
          <span className="font-bold text-lg">{stockInfo.symbol}</span>

          <Button variant="secondary" className="ml-auto text-neutral-400">
            Remove
          </Button>
        </div>

        <div>
          <div className="mb-3 flex items-end gap-3">
            <span
              className="font-bold text-2xl text-black"
              style={{ letterSpacing: "-4%" }}
            >
              {stockInfo.price.toFixed(2)}
            </span>
            <div className="flex items-center justify-center rounded-lg bg-muted px-2 py-2">
              <span
                className="font-bold text-muted-foreground text-xs"
                style={{ letterSpacing: "2%" }}
              >
                {isPositive ? "+" : ""}
                {stockInfo.changePercent.toFixed(2)}%
              </span>
            </div>
          </div>
          <p className="font-medium text-muted-foreground text-xs">
            Oct 25, 5:26:38PM UTC-4 . INDEXSP . Disclaimer
          </p>
        </div>

        <Sparkline
          data={chartData}
          color={chartColor}
          gradientColors={gradientColors}
          formatTooltip={formatTooltip}
        />
      </div>

      <div className="flex flex-col gap-4">
        <h2 className="font-bold text-lg">Details</h2>

        <StockDetailsList data={detailsData} />
      </div>

      <div className="flex flex-col gap-4">
        <h2 className="font-bold text-lg">About</h2>

        <p className="text-neutral-500 text-sm leading-6">
          Apple Inc. is an American multinational technology company that
          specializes in consumer electronics, computer software, and online
          services. Apple is the world's largest technology company by revenue
          (totalling $274.5 billion in 2020) and, since January 2021, the
          world's most valuable company. As of 2021, Apple is the world's
          fourth-largest PC vendor by unit sales, and fourth-largest smartphone
          manufacturer. It is one of the Big Five American information
          technology companies, along with Amazon, Google, Microsoft, and
          Facebook.
        </p>
      </div>
    </div>
  );
});

export default Stock;
