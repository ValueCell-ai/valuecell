import { Plus } from "lucide-react";
import { Outlet } from "react-router";
import StockSearchModal from "@/app/home/components/stock-search-modal";
import { Button } from "@/components/ui/button";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import StockList from "./components/stock-list";

export default function HomeLayout() {
  return (
    <div className="flex flex-1 overflow-hidden">
      <ScrollContainer className="flex-1">
        <Outlet />
      </ScrollContainer>

      <aside className="flex h-full min-w-62 flex-col justify-between border-l">
        <StockList />

        <StockSearchModal>
          <Button
            variant="secondary"
            className="mx-5 mb-6 font-bold text-sm hover:bg-gray-200"
          >
            <Plus size={16} />
            Add Stocks
          </Button>
        </StockSearchModal>
      </aside>
    </div>
  );
}
