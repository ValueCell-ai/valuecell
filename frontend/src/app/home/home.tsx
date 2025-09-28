import { useCallback, useMemo } from "react";
import { useNavigate } from "react-router";
import { useGetAgentList } from "@/api/agent";
import { useGetStockHistory, useGetStockPrice } from "@/api/stock";
import AgentAvatar from "@/components/valuecell/agent-avatar";
import { HOME_STOCK_SHOW } from "@/constants/stock";
import { TimeUtils } from "@/lib/time";
import { agentSuggestions } from "@/mock/agent-data";
import type { SparklineData } from "@/types/chart";
import {
  AgentRecommendList,
  AgentSuggestionsList,
  type SparklineStock,
  SparklineStockList,
} from "./components";

function Home() {
  const { data: agentList } = useGetAgentList();
  const navigate = useNavigate();

  const handleAgentClick = useCallback(
    (agentId: string) => {
      navigate(`/agent/${agentId}`);
    },
    [navigate],
  );

  // Get fixed stock tickers for homepage display
  const stockTickers = useMemo(() => {
    return HOME_STOCK_SHOW.map((stock) => stock.ticker);
  }, []);

  // Calculate date range for historical data
  const dateRange = useMemo(() => {
    const now = TimeUtils.nowUTC();
    const thirtyDaysAgo = now.subtract(30, "day");
    return {
      startDate: thirtyDaysAgo.toISOString(),
      endDate: now.toISOString(),
    };
  }, []);

  // Fetch stock price data for each ticker
  const stock1Price = useGetStockPrice({ ticker: stockTickers[0] || "" });
  const stock2Price = useGetStockPrice({ ticker: stockTickers[1] || "" });
  const stock3Price = useGetStockPrice({ ticker: stockTickers[2] || "" });

  // Fetch historical data for each stock (used for sparkline charts)
  const stock1History = useGetStockHistory({
    ticker: stockTickers[0] || "",
    interval: "d",
    start_date: dateRange.startDate,
    end_date: dateRange.endDate,
  });
  const stock2History = useGetStockHistory({
    ticker: stockTickers[1] || "",
    interval: "d",
    start_date: dateRange.startDate,
    end_date: dateRange.endDate,
  });
  const stock3History = useGetStockHistory({
    ticker: stockTickers[2] || "",
    interval: "d",
    start_date: dateRange.startDate,
    end_date: dateRange.endDate,
  });

  // Transform data format to SparklineStock
  const sparklineStocks = useMemo(() => {
    const stocks: SparklineStock[] = [];

    const stocksData = [
      {
        ticker: stockTickers[0],
        symbol: HOME_STOCK_SHOW[0]?.symbol,
        price: stock1Price,
        history: stock1History,
      },
      {
        ticker: stockTickers[1],
        symbol: HOME_STOCK_SHOW[1]?.symbol,
        price: stock2Price,
        history: stock2History,
      },
      {
        ticker: stockTickers[2],
        symbol: HOME_STOCK_SHOW[2]?.symbol,
        price: stock3Price,
        history: stock3History,
      },
    ];

    stocksData.forEach(({ ticker, symbol, price, history }) => {
      const priceData = price?.data;
      const historyData = history?.data;

      if (ticker && symbol && priceData && historyData) {
        // Convert historical data to sparkline format
        // UTC timestamp strings are converted to UTC millisecond timestamps for chart
        const sparklineData: SparklineData = historyData.prices.map(
          (pricePoint) => [
            TimeUtils.createUTC(pricePoint.timestamp).valueOf(),
            pricePoint.close_price,
          ],
        );

        // Extract current price (remove currency symbols and formatting)
        const currentPrice = parseFloat(
          priceData.price_formatted.replace(/[^0-9.-]/g, ""),
        );

        // Extract change percentage (remove % symbol)
        const changePercent = parseFloat(
          priceData.change_percent_formatted.replace(/[^0-9.-]/g, ""),
        );

        stocks.push({
          symbol: symbol,
          price: currentPrice,
          currency: "$", // Default USD, can be adjusted as needed
          changeAmount: priceData.change,
          changePercent: changePercent,
          sparklineData: sparklineData,
        });
      }
    });

    return stocks;
  }, [
    stockTickers,
    stock1Price,
    stock2Price,
    stock3Price,
    stock1History,
    stock2History,
    stock3History,
  ]);

  const recommendations = useMemo(() => {
    return agentList?.map((agent) => ({
      id: agent.agent_name,
      title: agent.agent_name,
      icon: <AgentAvatar agentName={agent.agent_name} className="size-8" />,
    }));
  }, [agentList]);

  return (
    <div className="flex flex-col gap-6 p-8">
      <h1 className="font-medium text-3xl">👋 Welcome to ValueCell !</h1>

      <SparklineStockList stocks={sparklineStocks} />

      <AgentSuggestionsList
        title="What can I help you？"
        suggestions={agentSuggestions.map((suggestion) => ({
          ...suggestion,
          onClick: () => handleAgentClick(suggestion.id),
        }))}
      />

      <AgentRecommendList
        title="Recommended Agents"
        recommendations={recommendations || []}
      />
    </div>
  );
}

export default Home;
