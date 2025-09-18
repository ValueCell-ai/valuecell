import { Plus, Search, X } from "lucide-react";
import { useState } from "react";
import { useAddStockToWatchlist, useGetStocksList } from "@/api/stock";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import ScrollContainer from "@/components/valuecell/scroll-container";
import { useDebounce } from "@/hooks/use-debounce";

interface StockSearchModalProps {
  children: React.ReactNode;
}

export default function StockSearchModal({ children }: StockSearchModalProps) {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, 300);
  const { data: stockList, isLoading } = useGetStocksList({
    query: debouncedQuery,
  });

  const { mutate: addStockToWatchlist } = useAddStockToWatchlist();

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent
        className="flex h-3/5 min-h-[400px] w-md flex-col gap-3 rounded-2xl bg-neutral-50 p-6"
        showCloseButton={false}
      >
        <header className="flex items-center justify-between">
          <DialogTitle className="font-semibold text-2xl text-neutral-900">
            Stock Search
          </DialogTitle>
          <DialogClose asChild>
            <Button size="icon" variant="ghost" className="cursor-pointer">
              <X className="size-6 text-neutral-400" />
            </Button>
          </DialogClose>
        </header>

        {/* Search Input */}
        <div className="flex items-center gap-4 rounded-lg bg-white p-4 focus-within:ring-1">
          <Search className="size-5 text-neutral-400" />
          <Input
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for stock name or code"
            className="border-none bg-transparent p-0 text-neutral-900 text-sm shadow-none placeholder:text-neutral-400 focus-visible:ring-0 focus-visible:ring-offset-0"
          />
        </div>

        {/* Search Results */}
        <ScrollContainer>
          {isLoading ? (
            <p className="p-4 text-center text-neutral-400 text-sm">
              Searching...
            </p>
          ) : stockList && stockList.length > 0 ? (
            <div className="rounded-lg bg-white py-2">
              {stockList.map((stock) => (
                <div
                  key={stock.ticker}
                  className="flex items-center justify-between px-4 py-2 transition-colors hover:bg-gray-50"
                >
                  <div className="flex flex-col gap-px">
                    <p className="text-neutral-900 text-sm">
                      {stock.display_name}
                    </p>
                    <p className="text-neutral-400 text-xs">{stock.ticker}</p>
                  </div>

                  <Button
                    size="sm"
                    className="cursor-pointer font-normal text-sm text-white"
                    onClick={() =>
                      addStockToWatchlist({ ticker: stock.ticker })
                    }
                  >
                    <Plus className="size-5" />
                    Watchlist
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            query &&
            !isLoading &&
            stockList &&
            stockList.length === 0 && (
              <p className="p-4 text-center text-neutral-400 text-sm">
                No related stocks found
              </p>
            )
          )}
        </ScrollContainer>
      </DialogContent>
    </Dialog>
  );
}
