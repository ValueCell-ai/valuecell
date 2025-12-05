import BackButton from "@valuecell/button/back-button";
import { memo, useMemo } from "react";
import { useNavigate, useParams } from "react-router";
import {
  useGetStockDetail,
  useGetStockPrice,
  useRemoveStockFromWatchlist,
} from "@/api/stock";
import { Button } from "@/components/ui/button";
import { useStockColors } from "@/store/settings-store";
import type { Route } from "./+types/stock";
import TradingViewAdvancedChart from "./components/TradingViewAdvancedChart";

function Stock() {
  const { stockId } = useParams<Route.LoaderArgs["params"]>();
  const navigate = useNavigate();
  // Use stockId as ticker to fetch real data from API
  const ticker = stockId || "";
  const stockColors = useStockColors();

  // Fetch current stock price data
  const {
    data: stockPriceData,
    isLoading: isPriceLoading,
    error: priceError,
  } = useGetStockPrice({
    ticker,
  });

  // Fetch stock detail data
  const {
    data: stockDetailData,
    isLoading: isDetailLoading,
    error: detailError,
  } = useGetStockDetail({
    ticker,
  });

  const removeStockMutation = useRemoveStockFromWatchlist();

  const handleRemoveStock = async () => {
    try {
      await removeStockMutation.mutateAsync(ticker);
      navigate(-1);
    } catch (error) {
      console.error("Failed to remove stock from watchlist:", error);
    }
  };

  // Create stock info from API data
  const stockInfo = useMemo(() => {
    if (!stockPriceData) return null;

    // Use display name from detail data if available, otherwise use ticker
    const companyName = stockDetailData?.display_name || ticker;

    return {
      symbol: ticker,
      companyName,
      price: stockPriceData.price_formatted,
      changePercent: stockPriceData.change_percent,
      currency: stockPriceData.currency,
      changeAmount: stockPriceData.change,
    };
  }, [stockPriceData, stockDetailData, ticker]);

  // Handle loading states
  if (isPriceLoading || isDetailLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-gray-500 text-lg">Loading stock data...</div>
      </div>
    );
  }

  // Handle error states
  if (priceError || detailError) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-lg text-red-500">
          Error loading stock data:{" "}
          {priceError?.message || detailError?.message}
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

  return (
    <div className="flex flex-col gap-8 bg-white px-8 py-6">
      <div className="flex flex-col gap-4">
        <BackButton />
        <div className="flex items-center gap-2">
          <span className="font-bold text-lg">{stockInfo.companyName}</span>
          <Button
            variant="secondary"
            className="ml-auto text-neutral-400"
            onClick={handleRemoveStock}
            disabled={removeStockMutation.isPending}
          >
            {removeStockMutation.isPending ? "Removing..." : "Remove"}
          </Button>
        </div>
      </div>
      <div className="w-full">
        <TradingViewAdvancedChart
          ticker={ticker}
          interval="D"
          minHeight={420}
          theme="light"
          colors={{
            upColor: stockColors.positive,
            downColor: stockColors.negative,
          }}
          locale="en"
          timezone="UTC"
        />
      </div>

      {/* <div className="flex flex-col gap-4">
        <h2 className="font-bold text-lg">Details</h2>

        <StockDetailsList data={detailsData} />
      </div> */}

      <div className="flex flex-col gap-4">
        <h2 className="font-bold text-lg">About</h2>

        <p className="line-clamp-4 text-neutral-500 text-sm leading-6">
          {stockDetailData?.properties?.business_summary}
        </p>

        {stockDetailData?.properties && (
          <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Sector:</span>
              <span className="ml-2 font-medium">
                {stockDetailData.properties.sector}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Industry:</span>
              <span className="ml-2 font-medium">
                {stockDetailData.properties.industry}
              </span>
            </div>
            {stockDetailData.properties.website && (
              <div className="col-span-2">
                <span className="text-muted-foreground">Website:</span>
                <a
                  href={stockDetailData.properties.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-2 text-blue-600 hover:underline"
                >
                  {stockDetailData.properties.website}
                </a>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(Stock);
