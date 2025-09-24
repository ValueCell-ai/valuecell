import BackButton from "@valuecell/button/back-button";
import Sparkline from "@valuecell/charts/sparkline";
import { StockIcon } from "@valuecell/menus/stock-menus";
import { memo, useMemo } from "react";
import { useParams } from "react-router";
import { StockDetailsList } from "@/app/home/components";
import { Button } from "@/components/ui/button";
import { STOCK_BADGE_COLORS } from "@/constants/stock";
import { formatChange, formatPrice, getChangeType } from "@/lib/utils";
import { stockData } from "@/mock/stock-data";
import type { SparklineData } from "@/types/chart";
import type { Route } from "./+types/stock";

// Generate historical price data in [timestamp, value] format
function generateHistoricalData(
  basePrice: number,
  days: number = 30,
): SparklineData {
  const data: SparklineData = [];
  const now = new Date();

  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);

    // Simulate price fluctuation (±5%)
    const variation = (Math.random() - 0.5) * 0.1;
    const price = basePrice * (1 + variation * (i / days)); // Add trend

    // Use [timestamp, value] format to match SparklineData
    data.push([
      date.valueOf(), // Use timestamp number instead of ISO string
      Math.max(0, Number(price.toFixed(2))),
    ]);
  }

  return data;
}

const Stock = memo(function Stock() {
  const { stockId } = useParams<Route.LoaderArgs["params"]>();

  // Find stock information from mock data
  const stockInfo = useMemo(() => {
    for (const group of stockData) {
      const stock = group.stocks.find((s) => s.symbol === stockId);
      if (stock) return stock;
    }
    return null;
  }, [stockId]);

  // Generate 60-day historical data (fixed, as per design)
  const chartData = useMemo(() => {
    if (!stockInfo) return [];
    return generateHistoricalData(stockInfo.price, 60);
  }, [stockInfo]);

  // Generate simulated detailed data
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

  if (!stockInfo) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-gray-500 text-lg">Stock {stockId} not found</div>
      </div>
    );
  }

  const changeType = getChangeType(stockInfo.changePercent);

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
          <div className="mb-3 flex items-center gap-3">
            <span className="font-bold text-2xl">
              {formatPrice(stockInfo.price, stockInfo.currency)}
            </span>
            <span
              className="rounded-lg p-2 font-bold text-xs"
              style={{
                backgroundColor: STOCK_BADGE_COLORS[changeType].bg,
                color: STOCK_BADGE_COLORS[changeType].text,
              }}
            >
              {formatChange(stockInfo.changePercent, "%")}
            </span>
          </div>
          <p className="font-medium text-muted-foreground text-xs">
            Oct 25, 5:26:38PM UTC-4 . INDEXSP . Disclaimer
          </p>
        </div>

        <Sparkline data={chartData} changeType={changeType} />
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
