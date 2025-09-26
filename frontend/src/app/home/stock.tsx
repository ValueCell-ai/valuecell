import BackButton from "@valuecell/button/back-button";
import Sparkline from "@valuecell/charts/sparkline";
import { StockIcon } from "@valuecell/menus/stock-menus";
import { memo, useMemo } from "react";
import { useParams } from "react-router";
import { useGetStockHistory, useGetStockPrice } from "@/api/stock";
import { StockDetailsList } from "@/app/home/components";
import { Button } from "@/components/ui/button";
import { STOCK_BADGE_COLORS } from "@/constants/stock";
import { TimeUtils } from "@/lib/time";
import { formatChange, formatPrice, getChangeType } from "@/lib/utils";
import type { SparklineData } from "@/types/chart";
import type { Route } from "./+types/stock";

const Stock = memo(function Stock() {
  const { stockId } = useParams<Route.LoaderArgs["params"]>();

  // Use stockId as ticker to fetch real data from API
  const ticker = stockId || "";

  // Fetch current stock price data
  const {
    data: stockPriceData,
    isLoading: isPriceLoading,
    error: priceError,
  } = useGetStockPrice({
    ticker,
  });

  // Calculate date range for 60-day historical data
  const dateRange = useMemo(() => {
    const endDate = TimeUtils.nowUTC().format("YYYY-MM-DD");
    const startDate = TimeUtils.subtract(TimeUtils.nowUTC(), 60, "day").format(
      "YYYY-MM-DD",
    );
    return { startDate, endDate };
  }, []);

  // Fetch historical data for chart
  const {
    data: stockHistoryData,
    isLoading: isHistoryLoading,
    error: historyError,
  } = useGetStockHistory({
    ticker,
    interval: "d",
    start_date: dateRange.startDate,
    end_date: dateRange.endDate,
  });

  // Transform historical data to chart format
  const chartData = useMemo(() => {
    if (!stockHistoryData?.prices) return [];

    // Convert UTC timestamp strings to UTC millisecond timestamps for chart
    const sparklineData: SparklineData = stockHistoryData.prices.map(
      (price) => [
        TimeUtils.createUTC(price.timestamp).valueOf(),
        price.close_price,
      ],
    );

    return sparklineData;
  }, [stockHistoryData]);

  // Create stock info from API data
  const stockInfo = useMemo(() => {
    if (!stockPriceData) return null;

    const currentPrice = parseFloat(
      stockPriceData.price_formatted.replace(/[^0-9.-]/g, ""),
    );
    const changePercent = parseFloat(
      stockPriceData.change_percent_formatted.replace(/[^0-9.-]/g, ""),
    );

    return {
      symbol: ticker,
      companyName: ticker, // Use ticker as company name since we don't have company name in API
      price: stockPriceData.price_formatted,
      changePercent: stockPriceData.change_percent_formatted,
      currency: "$", // Default to USD
      changeAmount: stockPriceData.change,
      changePercentNumeric: changePercent,
      priceNumeric: currentPrice,
    };
  }, [stockPriceData, ticker]);

  // Create details data from API response
  const detailsData = useMemo(() => {
    if (!stockPriceData || !stockHistoryData?.prices) return undefined;

    // Calculate previous close, day range from historical data
    const prices = stockHistoryData.prices;
    const todayPrices = prices.slice(-1)[0]; // Last day's data
    const yesterdayPrices = prices.slice(-2, -1)[0]; // Previous day's data

    // Get min/max from recent prices for day range
    const recentPrices = prices.slice(-5); // Last 5 days
    const dayLow = Math.min(...recentPrices.map((p) => p.low_price));
    const dayHigh = Math.max(...recentPrices.map((p) => p.high_price));

    // Get min/max from all historical data for year range
    const yearLow = Math.min(...prices.map((p) => p.low_price));
    const yearHigh = Math.max(...prices.map((p) => p.high_price));

    return {
      previousClose: yesterdayPrices?.close_price?.toFixed(2) || "N/A",
      dayRange: `${dayLow.toFixed(2)} - ${dayHigh.toFixed(2)}`,
      yearRange: `${yearLow.toFixed(2)} - ${yearHigh.toFixed(2)}`,
      marketCap: stockPriceData.market_cap_formatted || "N/A",
      volume: todayPrices?.volume?.toLocaleString() || "N/A",
      dividendYield: "N/A", // Not available in current API
    };
  }, [stockPriceData, stockHistoryData]);

  // Handle loading states
  if (isPriceLoading || isHistoryLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-gray-500 text-lg">Loading stock data...</div>
      </div>
    );
  }

  // Handle error states
  if (priceError || historyError) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-lg text-red-500">
          Error loading stock data:{" "}
          {priceError?.message || historyError?.message}
        </div>
      </div>
    );
  }

  // Handle no data found
  if (!stockInfo || !stockPriceData) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-gray-500 text-lg">Stock {stockId} not found</div>
      </div>
    );
  }

  const changeType = getChangeType(stockInfo.changePercentNumeric);

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
              {formatPrice(stockInfo.priceNumeric, stockInfo.currency)}
            </span>
            <span
              className="rounded-lg p-2 font-bold text-xs"
              style={{
                backgroundColor: STOCK_BADGE_COLORS[changeType].bg,
                color: STOCK_BADGE_COLORS[changeType].text,
              }}
            >
              {formatChange(stockInfo.changePercentNumeric, "%")}
            </span>
          </div>
          <p className="font-medium text-muted-foreground text-xs">
            {/* Convert UTC timestamp to local time for display */}
            {TimeUtils.fromUTC(stockPriceData.timestamp).format(
              "MMM DD, YYYY h:mm:ss A",
            )}{" "}
            . {stockPriceData.source} . Disclaimer
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
          {ticker} stock information and trading data. Real-time price updates
          and historical performance data are provided through our financial
          data API. Please consult with a financial advisor before making
          investment decisions.
        </p>
      </div>
    </div>
  );
});

export default Stock;
