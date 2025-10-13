import { memo, useMemo } from "react";
import { useLocation } from "react-router";
import { useGetStockPrice, useGetWatchlist } from "@/api/stock";
import {
  StockMenu,
  StockMenuGroup,
  StockMenuGroupHeader,
  StockMenuHeader,
  StockMenuListItem,
} from "@/components/valuecell/menus/stock-menus";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import type { Stock } from "@/types/stock";

function StockList() {
  const { pathname } = useLocation();
  const { data: stockList } = useGetWatchlist();

  const stockData = useMemo(() => {
    return stockList?.map((group) => ({
      title: group.name,
      stocks: group.items,
    }));
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
        changePercent: stockPrice?.change_percent_formatted ?? "N/A",
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
      <StockMenuHeader>My Stocks</StockMenuHeader>
      <ScrollContainer>
        {stockData?.map((group) => (
          <StockMenuGroup key={group.title}>
            <StockMenuGroupHeader>{group.title}</StockMenuGroupHeader>
            {group.stocks.map((stock) => (
              <StockItem key={stock.symbol} stock={stock} />
            ))}
          </StockMenuGroup>
        ))}
      </ScrollContainer>
    </StockMenu>
  );
}

export default memo(StockList);
