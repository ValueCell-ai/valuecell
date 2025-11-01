import { useMemo } from "react";
import { useGetStockHistory, useGetStockPrice } from "@/api/stock";
import { TimeUtils } from "@/lib/time";
import type { SparklineData } from "@/types/chart";
import type { StockInterval } from "@/types/stock";
import type { SparklineStock } from "../components/sparkline-stock-list";

interface StockConfig {
  ticker: string;
  symbol: string;
}

interface UseSparklineStocksOptions {
  /** Number of days for historical data */
  historyDays?: number;
  /** Data interval for historical data (default: "1d") */
  interval?: StockInterval;
}

/**
 * Custom hook to aggregate stock data for sparkline display
 * Fetches price and historical data for multiple stocks and transforms them into SparklineStock format
 */
export function useSparklineStocks(
  stocks: readonly StockConfig[],
  options: UseSparklineStocksOptions = {},
) {
  const { historyDays = 30, interval = "1d" } = options;

  // Calculate date range for historical data
  const dateRange = useMemo(() => {
    const now = TimeUtils.nowUTC();
    const startDate = now.subtract(historyDays, "day");
    return {
      startDate: startDate.toISOString(),
      endDate: now.toISOString(),
    };
  }, [historyDays]);

  // Extract tickers for easier access
  const tickers = useMemo(() => stocks.map((stock) => stock.ticker), [stocks]);

  // Fetch stock price data for each ticker (up to 3 stocks as per current usage)
  const stock1Price = useGetStockPrice({ ticker: tickers[0] || "" });
  const stock2Price = useGetStockPrice({ ticker: tickers[1] || "" });
  const stock3Price = useGetStockPrice({ ticker: tickers[2] || "" });

  // Fetch historical data for each stock (up to 3 stocks as per current usage)
  const stock1History = useGetStockHistory({
    ticker: tickers[0] || "",
    interval,
    start_date: dateRange.startDate,
    end_date: dateRange.endDate,
  });
  const stock2History = useGetStockHistory({
    ticker: tickers[1] || "",
    interval,
    start_date: dateRange.startDate,
    end_date: dateRange.endDate,
  });
  const stock3History = useGetStockHistory({
    ticker: tickers[2] || "",
    interval,
    start_date: dateRange.startDate,
    end_date: dateRange.endDate,
  });

  // Transform data format to SparklineStock
  // Only depend on actual data, not query objects, to prevent unnecessary re-renders
  // biome-ignore lint/correctness/useExhaustiveDependencies: Only depend on data, not query objects, to prevent unnecessary re-renders
  const sparklineStocks = useMemo(() => {
    const result: SparklineStock[] = [];
    const priceQueries = [stock1Price, stock2Price, stock3Price];
    const historyQueries = [stock1History, stock2History, stock3History];

    stocks.forEach((stock, index) => {
      const priceQuery = priceQueries[index];
      const historyQuery = historyQueries[index];

      const priceData = priceQuery?.data;
      const historyData = historyQuery?.data;

      if (stock.ticker && stock.symbol && priceData && historyData) {
        // Convert historical data to sparkline format
        // UTC timestamp strings are converted to UTC millisecond timestamps for chart
        const sparklineData: SparklineData = historyData.prices.map(
          (pricePoint) => [
            TimeUtils.createUTC(pricePoint.timestamp).valueOf(),
            pricePoint.close_price,
          ],
        );

        result.push({
          symbol: stock.symbol,
          price: priceData.price,
          currency: priceData.currency || "USD", // Use actual currency from API
          changeAmount: priceData.change,
          changePercent: priceData.change_percent,
          sparklineData: sparklineData,
        });
      }
    });

    return result;
  }, [
    stocks,
    stock1Price.data,
    stock2Price.data,
    stock3Price.data,
    stock1History.data,
    stock2History.data,
    stock3History.data,
  ]);

  // Group queries for easier processing
  const priceQueries = [stock1Price, stock2Price, stock3Price];
  const historyQueries = [stock1History, stock2History, stock3History];

  // Calculate loading states
  const isLoadingPrices = priceQueries.some((query) => query.isLoading);
  const isLoadingHistory = historyQueries.some((query) => query.isLoading);
  const isLoading = isLoadingPrices || isLoadingHistory;

  // Calculate error states
  const priceErrors = priceQueries.filter((query) => query.error);
  const historyErrors = historyQueries.filter((query) => query.error);
  const hasErrors = priceErrors.length > 0 || historyErrors.length > 0;

  return {
    sparklineStocks,
    isLoading,
    hasErrors,
    priceErrors,
    historyErrors,
  };
}
