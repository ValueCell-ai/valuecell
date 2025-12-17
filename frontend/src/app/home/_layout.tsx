import { Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Outlet } from "react-router";
import { Button } from "@/components/ui/button";
import { StockList, StockSearchModal } from "./components";

export default function HomeLayout() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-hidden bg-muted py-4 pr-4 pl-2">
      <h1 className="font-medium text-3xl">{t("home.welcome")}</h1>

      <div className="flex flex-1 gap-3 overflow-hidden">
        <main className="scroll-container flex-1 rounded-lg bg-card">
          <Outlet />
        </main>

        <aside className="flex w-72 flex-col overflow-hidden rounded-lg bg-card">
          <StockList />

          <StockSearchModal>
            <Button
              variant="secondary"
              className="mx-5 mb-6 font-bold text-sm"
            >
              <Plus size={16} />
              {t("home.stock.add")}
            </Button>
          </StockSearchModal>
        </aside>
      </div>
    </div>
  );
}
