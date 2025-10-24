import { useState } from "react";
import { useNavigate } from "react-router";
import AppConversationSheet from "@/components/valuecell/app-conversation-sheet";
import { HOME_STOCK_SHOW } from "@/constants/stock";
import { agentSuggestions } from "@/mock/agent-data";
import ChatInputArea from "../agent/components/chat-conversation/chat-input-area";
import { AgentSuggestionsList, SparklineStockList } from "./components";
import { useSparklineStocks } from "./hooks/use-sparkline-stocks";

function Home() {
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState<string>("");

  const handleAgentClick = (agentId: string) => {
    navigate(`/agent/${agentId}`);
  };

  const { sparklineStocks } = useSparklineStocks(HOME_STOCK_SHOW);

  return (
    <div className="flex h-full min-w-[800px] flex-col gap-4 px-2">
      <SparklineStockList stocks={sparklineStocks} />

      <section className="relative flex flex-1 flex-col items-center justify-center gap-12 rounded-xl bg-white py-8">
        <div className="absolute top-2 left-2">
          <AppConversationSheet />
        </div>

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
    </div>
  );
}

export default Home;
