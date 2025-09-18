import { memo } from "react";
import { useLocation } from "react-router";
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
