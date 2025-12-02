import { Outlet } from "react-router";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";

export default function HomeLayout() {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-hidden bg-gray-100 py-4 pr-4 pl-2">
      <h1 className="font-medium text-3xl">👋 Welcome to ValueCell !</h1>

      <div className="flex flex-1 gap-3 overflow-hidden">
        <main className="h-full flex-1 overflow-hidden rounded-lg">
          <ScrollContainer className="h-full">
            <Outlet />
          </ScrollContainer>
        </main>

        {/* <aside className="flex min-w-62 max-w-80 flex-col justify-between rounded-lg bg-white">
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
        </aside> */}
      </div>
    </div>
  );
}
