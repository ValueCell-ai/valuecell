import { Plus } from "lucide-react";
import { Outlet } from "react-router";
import { Button } from "@/components/ui/button";
import { StockList, StockSearchModal } from "./components";

export default function HomeLayout() {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-hidden bg-gray-100 py-4 pr-4 pl-2">
      <h1 className="font-medium text-3xl">👋 Welcome to ValueCell !</h1>

      <div className="flex min-h-0 flex-1 gap-3 overflow-hidden">
        <main className="scroll-container h-full min-h-0 flex-1 rounded-lg">
          <Outlet />
        </main>

        {
          <aside className="flex h-full min-h-0 min-w-62 max-w-80 flex-col overflow-hidden rounded-lg bg-white">
            <div className="min-h-0 flex-1 overflow-hidden">
              <StockList />
            </div>

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
        }
      </div>
    </div>
  );
}
