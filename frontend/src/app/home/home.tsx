import { useState } from "react";
import { useNavigate } from "react-router";
import { useAllPollTaskList } from "@/api/conversation";
import { agentSuggestions } from "@/mock/agent-data";
import ChatInputArea from "../agent/components/chat-conversation/chat-input-area";
import { AgentSuggestionsList, AgentTaskCards } from "./components";
import TradingViewTickerTape from "./components/tradingview-ticker-tape";

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
    <div className="flex h-full min-w-[800px] flex-col gap-3">
      {allPollTaskList && allPollTaskList.length > 0 ? (
        <section className="flex w-full flex-1 flex-col items-center justify-between gap-4">
          <TradingViewTickerTape symbols={INDEX_SYMBOLS} />

          <div className="scroll-container flex-1">
            <AgentTaskCards tasks={allPollTaskList} />
          </div>

          <ChatInputArea
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
        <section className="flex w-full flex-1 flex-col items-center gap-8 rounded-lg bg-white px-6 pt-12">
          <TradingViewTickerTape symbols={INDEX_SYMBOLS} />

          <h1 className="mt-16 font-medium text-3xl text-gray-950">
            👋 Hello Investor!
          </h1>

          <ChatInputArea
            className="w-4/5 max-w-[800px]"
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
