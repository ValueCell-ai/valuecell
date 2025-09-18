import { memo } from "react";
import { useLocation } from "react-router";
// TODO: 重新实现 API 调用，orval 已移除
// import { useGetUserWatchlistsApiV1WatchlistUserIdGet } from "@/api/generated";
import {
  StockMenu,
  StockMenuGroup,
  StockMenuGroupHeader,
  StockMenuHeader,
  StockMenuListItem,
} from "@/components/valuecell/menus/stock-menus";
import ScrollContainer from "@/components/valuecell/scroll-container";
import { stockData } from "@/mock/stock-data";

function StockList() {
  const { pathname } = useLocation();

  // Extract stock symbol (e.g., AAPL) from path like /stock/AAPL
  const stockSymbol = pathname.split("/")[2];

  // TODO: 重新实现 API 调用，orval 已移除
  // const { data: watchlist } =
  //   useGetUserWatchlistsApiV1WatchlistUserIdGet("default_user");
  // console.log("🚀 ~ StockList ~ watchlist:", watchlist);
  const watchlist = null;

  return (
    <StockMenu>
      <StockMenuHeader>My Stocks</StockMenuHeader>
      <ScrollContainer>
        {stockData.map((group) => (
          <StockMenuGroup key={group.title}>
            <StockMenuGroupHeader>{group.title}</StockMenuGroupHeader>
            {group.stocks.map((stock) => (
              <StockMenuListItem
                key={stock.symbol}
                stock={stock}
                to={`/stock/${stock.symbol}`}
                isActive={stockSymbol === stock.symbol}
                replace={!!stockSymbol}
              />
            ))}
          </StockMenuGroup>
        ))}
      </ScrollContainer>
    </StockMenu>
  );
}

export default memo(StockList);
