import { useState } from "react";
// TODO: 重新实现 API 调用，orval 已移除
// import {
//   useAddStockToWatchlistApiV1WatchlistUserIdStocksPost,
//   useSearchAssetsApiV1WatchlistSearchGet,
// } from "@/api/generated";
// import type { AssetInfoData } from "@/api/model";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

const imgSousuo31 =
  "http://localhost:3845/assets/a0d762e5297b09f6ad2e47d6d8f323b53dcc81aa.svg";

interface StockSearchModalProps {
  children: React.ReactNode;
}

export default function StockSearchModal({ children }: StockSearchModalProps) {
  const [searchValue, setSearchValue] = useState("");

  // TODO: 重新实现 API 调用，orval 已移除
  // const { data, isLoading, } = useSearchAssetsApiV1WatchlistSearchGet(
  //   {
  //     q: searchValue,
  //   },
  //   {
  //     query: {
  //       enabled: !!searchValue,
  //     },
  //   },
  // );

  // 临时模拟数据
  const data = null;
  const isLoading = false;

  // Extract results safely
  const results = data?.data?.data?.results ?? [];

  // TODO: 重新实现添加股票到监视列表的功能
  // const { mutate: addStockToWatchlist } =
  //   useAddStockToWatchlistApiV1WatchlistUserIdStocksPost();
  const addStockToWatchlist = () => {
    console.log("addStockToWatchlist: 功能已禁用，需要重新实现");
  };

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent
        className="w-full max-w-md rounded-[20px] border-none bg-[#f4f4f4] p-6"
        showCloseButton={false}
      >
        <div className="flex flex-col gap-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <DialogTitle className="font-semibold text-[20px] text-gray-950 leading-[28px]">
              Stock Search
            </DialogTitle>
            <DialogClose asChild>
              <button
                type="button"
                className="rounded-sm p-1 transition-colors hover:bg-gray-200"
              >
                <div className="relative flex h-6 w-6 items-center justify-center">
                  <div className="absolute rotate-45">
                    <div className="h-[1.331px] w-[21.296px] rounded-[8.652px] bg-[#838383]" />
                  </div>
                  <div className="absolute rotate-[135deg]">
                    <div className="h-[1.331px] w-[21.296px] rounded-[8.652px] bg-[#838383]" />
                  </div>
                </div>
              </button>
            </DialogClose>
          </div>

          {/* Search Input */}
          <div className="flex items-center gap-4 rounded-[11px] border border-gray-100 bg-white p-4">
            <div className="h-5 w-5 flex-shrink-0">
              <img src={imgSousuo31} alt="Search" className="h-full w-full" />
            </div>
            <Input
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              placeholder="Search for stock name or code"
              className="border-none bg-transparent p-0 text-[14px] text-gray-950 placeholder:text-gray-400 focus-visible:ring-0 focus-visible:ring-offset-0"
            />
          </div>

          {/* Search Results */}
          {searchValue && (
            <div className="max-h-60 overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center p-4">
                  <div className="text-gray-500 text-sm">搜索中...</div>
                </div>
              ) : results.length > 0 ? (
                <div className="rounded-[8px] bg-white py-[8px]">
                  {results.map((asset: any) => (
                    <div
                      key={asset.ticker}
                      className="flex items-center justify-between px-[16px] py-[4px] transition-colors hover:bg-gray-50"
                    >
                      <div className="flex flex-col gap-px">
                        <p className="text-[14px] text-gray-900">
                          {asset.display_name}
                        </p>
                        <p className="text-[12px] text-gray-300">
                          {asset.ticker}
                        </p>
                      </div>
                      <button
                        type="button"
                        className="relative h-[28px] w-[76px] rounded-[6px] bg-gray-950"
                        onClick={() => {
                          addStockToWatchlist();
                        }}
                      >
                        {/* Plus icon */}
                        <div className="absolute top-[7px] left-[8px]">
                          <div className="absolute top-[13.5px] left-[8px] h-px w-[14px] bg-white" />
                          <div className="absolute top-[7px] left-[14.5px] flex h-[14px] w-[1px] items-center justify-center">
                            <div className="h-px w-[14px] rotate-[270deg] bg-white" />
                          </div>
                        </div>
                        <p className="absolute top-[4px] left-[26px] font-normal text-[14px] text-white leading-[20px]">
                          加自选
                        </p>
                      </button>
                    </div>
                  ))}
                </div>
              ) : searchValue.length > 0 ? (
                <div className="flex items-center justify-center p-4">
                  <div className="text-gray-500 text-sm">未找到相关股票</div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
