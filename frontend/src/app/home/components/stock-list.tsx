import { memo, useMemo } from "react";
import { useLocation } from "react-router";
import { useGetStockPrice, useGetWatchlist } from "@/api/stock";
import {
  StockMenu,
  StockMenuHeader,
  StockMenuListItem,
} from "@/components/valuecell/menus/stock-menus";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import type { Stock } from "@/types/stock";

function StockList() {
  const { pathname } = useLocation();
  const { data: stockList } = useGetWatchlist();

  const stockData = useMemo(() => {
    const allStocks = stockList?.flatMap((group) => group.items) ?? [];
    return allStocks;
  }, [stockList]);

  // Extract stock symbol (e.g., AAPL) from path like /stock/AAPL
  const stockTicker = pathname.split("/")[3];

  // define a stock item component
  const StockItem = ({ stock }: { stock: Stock }) => {
    const { data: stockPrice } = useGetStockPrice({ ticker: stock.ticker });

    // transform data format to match StockMenuListItem expectation
    const transformedStock = useMemo(
      () => ({
        symbol: stock.symbol,
        companyName: stock.display_name,
        price: stockPrice?.price_formatted ?? "N/A",
        currency: stockPrice?.currency ?? "USD",
        changeAmount: stockPrice?.change ?? 0,
        changePercent: stockPrice?.change_percent ?? null,
      }),
      [stock, stockPrice],
    );

    return (
      <StockMenuListItem
        stock={transformedStock}
        to={`/home/stock/${stock.ticker}`}
        isActive={stockTicker === stock.ticker}
        replace={!!stockTicker}
      />
    );
  };

  return (
    <StockMenu>
      <StockMenuHeader>My Watchlist</StockMenuHeader>
      <ScrollContainer>
        {stockData?.map((stock) => (
          <StockItem key={stock.symbol} stock={stock} />
        ))}
      </ScrollContainer>
    </StockMenu>
  );
}

export default memo(StockList);
