import { useState } from "react";
import { useNavigate } from "react-router";
import { useAllPollTaskList } from "@/api/conversation";
import { agentSuggestions } from "@/mock/agent-data";
import ChatInputArea from "../agent/components/chat-conversation/chat-input-area";
import { AgentSuggestionsList, AgentTaskCards } from "./components";

function Home() {
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState<string>("");

  const { data: allPollTaskList } = useAllPollTaskList();

  // Get region-aware default tickers from API
  // const { data: defaultTickersData } = useGetDefaultTickers();

  // Use API-returned tickers, fallback to hardcoded values if API fails
  // const stockConfig = useMemo(() => {
  //   if (defaultTickersData?.tickers) {
  //     return defaultTickersData.tickers.map((t) => ({
  //       ticker: t.ticker,
  //       symbol: t.symbol,
  //     }));
  //   }
  //   // Fallback to hardcoded values
  //   return [...HOME_STOCK_SHOW];
  // }, [defaultTickersData]);

  // const { sparklineStocks } = useSparklineStocks(stockConfig);

  const handleAgentClick = (agentId: string) => {
    navigate(`/agent/${agentId}`);
  };

  return (
    <div className="flex h-full min-w-[800px] flex-col gap-3">
      {/* <SparklineStockList stocks={sparklineStocks} /> */}

      {allPollTaskList && allPollTaskList.length > 0 ? (
        <section className="flex flex-1 flex-col items-center justify-between gap-4 overflow-hidden">
          <div className="scroll-container w-full">
            <AgentTaskCards tasks={allPollTaskList} />
          </div>

          <ChatInputArea
            className="w-full"
            value={inputValue}
            onChange={(value) => setInputValue(value)}
            onSend={() =>
              navigate("/agent/ValueCellAgent", {
                state: {
                  inputValue,
                },
              })
            }
          />
        </section>
      ) : (
        <section className="flex w-full flex-1 flex-col items-center justify-center gap-8 overflow-hidden rounded-lg bg-white py-8">
          <div className="space-y-4 text-center text-gray-950">
            <h1 className="font-medium text-3xl">👋 Hello Investor!</h1>
            <p>
              You can analyze and track the stock information you want to know
            </p>
          </div>

          <ChatInputArea
            className="w-3/4 max-w-[800px]"
            value={inputValue}
            onChange={(value) => setInputValue(value)}
            onSend={() =>
              navigate("/agent/ValueCellAgent", {
                state: {
                  inputValue,
                },
              })
            }
          />

          <AgentSuggestionsList
            suggestions={agentSuggestions.map((suggestion) => ({
              ...suggestion,
              onClick: () => handleAgentClick(suggestion.id),
            }))}
          />
        </section>
      )}
    </div>
  );
}

export default Home;
