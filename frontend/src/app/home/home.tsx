import { useState } from "react";
import { useNavigate } from "react-router";
import { useAllPollTaskList } from "@/api/conversation";
import { agentSuggestions } from "@/mock/agent-data";
import ChatInputArea from "../agent/components/chat-conversation/chat-input-area";
import { AgentSuggestionsList, AgentTaskCards } from "./components";
import TradingViewTickerTape from "./components/TradingViewTickerTape";

const INDEX_SYMBOLS = [
  "FOREXCOM:SPXUSD",
  "NASDAQ:IXIC",
  "NASDAQ:NDX",
  "INDEX:HSI",
  "SSE:000001",
  "BINANCE:BTCUSDT",
  "BINANCE:ETHUSDT",
];

function Home() {
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState<string>("");

  const { data: allPollTaskList } = useAllPollTaskList();

  const handleAgentClick = (agentId: string) => {
    navigate(`/agent/${agentId}`);
  };

  return (
    <div className="scroll-container flex min-h-svh min-w-[800px] flex-col gap-3 pb-4">
      {allPollTaskList && allPollTaskList.length > 0 ? (
        <section className="flex h-full flex-1 flex-col items-center justify-between gap-4 overflow-hidden">
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
        <section className="flex h-full w-full flex-1 flex-col items-center gap-8 overflow-hidden rounded-lg bg-white pt-12">
          <div className="mx-auto w-4/5 max-w-[800px] px-4">
            <TradingViewTickerTape symbols={INDEX_SYMBOLS} />
          </div>
          <div className="mt-16 space-y-4 text-center text-gray-950">
            <h1 className="font-medium text-3xl">👋 Hello Investor!</h1>
          </div>

          <div className="flex w-full max-w-[800px] flex-col gap-4 px-4">
            {/* Index section redesigned to ticker tape */}
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
