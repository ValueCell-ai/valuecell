import { useState } from "react";
import { useNavigate } from "react-router";
import { useAllPollTaskList } from "@/api/conversation";
import { useGetDefaultTickers } from "@/api/system";
import { agentSuggestions } from "@/mock/agent-data";
import ChatInputArea from "../agent/components/chat-conversation/chat-input-area";
import { AgentSuggestionsList, AgentTaskCards, StockCard } from "./components";

function Home() {
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState<string>("");

  const { data: allPollTaskList } = useAllPollTaskList();
  const { data: defaultTickersData } = useGetDefaultTickers();

  const handleAgentClick = (agentId: string) => {
    navigate(`/agent/${agentId}`);
  };

  const tickers = defaultTickersData?.tickers || [];

  return (
    <div className="flex h-full min-w-[800px] flex-col gap-3 overflow-y-auto pb-4">
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
        <section className="flex w-full flex-col items-center gap-8 overflow-visible rounded-lg bg-white py-8">
          <div className="space-y-4 text-center text-gray-950">
            <h1 className="font-medium text-3xl">👋 Hello Investor!</h1>

          </div>

          <div className="flex w-full max-w-[800px] flex-col gap-4 px-4">
            <div className="flex w-full justify-center gap-4">
              {tickers.slice(0, 3).map((ticker) => (
                <StockCard key={ticker.ticker} ticker={ticker.ticker} />
              ))}
            </div>
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

          <div className="flex w-full max-w-[800px] flex-col gap-4 px-4">
            <div className="grid grid-cols-3 gap-4">
              {agentSuggestions.map((suggestion) => (
                <AgentSuggestionsList
                  key={suggestion.id}
                  suggestions={[
                    {
                      ...suggestion,
                      onClick: () => handleAgentClick(suggestion.id),
                    },
                  ]}
                />
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default Home;
