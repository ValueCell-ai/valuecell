import { Plus, Search, X } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useAddStockToWatchlist,
  useGetStocksList,
  useGetWatchlist,
} from "@/api/stock";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useDebounce } from "@/hooks/use-debounce";
import type { Stock, Watchlist } from "@/types/stock";

interface StockSearchModalProps {
  children: React.ReactNode;
}

const StockItem = ({ stock }: { stock: Stock }) => {
  const { t } = useTranslation();
  const {
    mutateAsync: addStockToWatchlist,
    isPending: isPendingAddStockToWatchlist,
  } = useAddStockToWatchlist();

  // Use the hook instead of getQueryData to create a reactive subscription
  // This ensures the component re-renders when watchlist updates
  const { data: watchlist } = useGetWatchlist();

  // Check if the stock is already in the watchlist
  const isStockInWatchlist = watchlist?.some((item: Watchlist) =>
    item.items.some(
      (watchlistItem: Stock) => watchlistItem.ticker === stock.ticker,
    ),
  );

  return (
    <div
      key={stock.ticker}
      className="flex items-center justify-between px-4 py-2 transition-colors hover:bg-muted"
    >
      <div className="flex flex-col gap-px">
        <p className="text-foreground text-sm">{stock.display_name}</p>
        <p className="text-muted-foreground text-xs">{stock.ticker}</p>
      </div>

      <Button
        disabled={isPendingAddStockToWatchlist || isStockInWatchlist}
        size="sm"
        className="cursor-pointer font-normal text-sm"
        onClick={async () =>
          await addStockToWatchlist({ ticker: stock.ticker })
        }
      >
        {isPendingAddStockToWatchlist && (
          <>
            <Spinner className="size-5" />
            {t("home.search.action.watching")}
          </>
        )}
        {!isStockInWatchlist && (
          <>
            <Plus className="size-5" />
            {t("home.search.action.watch")}
          </>
        )}
        {isStockInWatchlist && <>{t("home.search.action.watched")}</>}
      </Button>
    </div>
  );
};

export default function StockSearchModal({ children }: StockSearchModalProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, 300);
  const { data: stockList, isLoading } = useGetStocksList({
    query: debouncedQuery,
  });

  const filteredStockList = (stockList || []).filter((stock) => {
    const assetType = stock.asset_type?.toLowerCase();
    const exchange = (stock.exchange || "").toUpperCase();
    const prefix = (stock.ticker?.split(":")[0] || "").toUpperCase();

    const US_EXCHANGES = new Set(["NASDAQ", "NYSE", "AMEX"]);
    const CN_EXCHANGES = new Set(["SSE", "SZSE", "HKEX"]);
    const JP_EXCHANGES = new Set(["TSE", "JPX", "TYO"]);

    const isCrypto = assetType === "crypto" || prefix === "CRYPTO";
    const isUS = US_EXCHANGES.has(exchange) || US_EXCHANGES.has(prefix);
    const isCN = CN_EXCHANGES.has(exchange) || CN_EXCHANGES.has(prefix);
    const isJP = JP_EXCHANGES.has(exchange) || JP_EXCHANGES.has(prefix);

    const isStock = assetType === "stock";

    return isCrypto || (isStock && (isUS || isCN || isJP));
  });

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent
        className="flex h-3/5 min-h-[400px] w-md flex-col gap-3 rounded-2xl bg-card p-6"
        showCloseButton={false}
      >
        <header className="flex items-center justify-between">
          <DialogTitle className="font-semibold text-2xl text-foreground">
            {t("home.search.title")}
          </DialogTitle>
          <DialogClose asChild>
            <Button size="icon" variant="ghost" className="cursor-pointer">
              <X className="size-6 text-muted-foreground" />
            </Button>
          </DialogClose>
        </header>

        {/* Search Input */}
        <div className="flex items-center gap-4 rounded-lg bg-background px-4 py-2 focus-within:ring-2 focus-within:ring-ring/50 hover:ring-1 hover:ring-border">
          <Search className="size-5 text-muted-foreground" />
          <Input
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("home.search.placeholder")}
            className="border-none bg-transparent p-0 text-foreground text-sm shadow-none placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0"
          />
        </div>

        {/* Search Results */}
        <div className="scroll-container">
          {isLoading ? (
            <p className="p-4 text-center text-muted-foreground text-sm">
              {t("home.search.searching")}
            </p>
          ) : filteredStockList && filteredStockList.length > 0 ? (
            <div className="rounded-lg bg-background py-2">
              {filteredStockList.map((stock) => (
                <StockItem key={stock.ticker} stock={stock} />
              ))}
            </div>
          ) : (
            query &&
            !isLoading &&
            stockList &&
            filteredStockList.length === 0 && (
              <p className="p-4 text-center text-muted-foreground text-sm">
                {t("home.search.noResults")}
              </p>
            )
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
