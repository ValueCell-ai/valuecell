import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { useAllPollTaskList } from "@/api/conversation";
import { IconGroupPng, MessageGroupPng, TrendPng } from "@/assets/png";
import { AutoTrade, NewsPush, ResearchReport } from "@/assets/svg";
import TradingViewTickerTape from "@/components/tradingview/tradingview-ticker-tape";
import SvgIcon from "@/components/valuecell/icon/svg-icon";
import { getTradingViewLocale } from "@/lib/utils";
import ChatInputArea from "../agent/components/chat-conversation/chat-input-area";
import { AgentSuggestionsList, AgentTaskCards } from "./components";

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
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState<string>("");

  const { data: allPollTaskList } = useAllPollTaskList();

  const handleAgentClick = (agentId: string) => {
    navigate(`/agent/${agentId}`);
  };

  const suggestions = [
    {
      id: "ResearchAgent",
      title: t("home.suggestions.research.title"),
      icon: <SvgIcon name={ResearchReport} />,
      description: t("home.suggestions.research.description"),
      bgColor:
        "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#E7EFFF]/70 to-[100%]",
      decorativeGraphics: <img src={IconGroupPng} alt="IconGroup" />,
    },
    {
      id: "StrategyAgent",
      title: t("home.suggestions.strategy.title"),
      icon: <SvgIcon name={AutoTrade} />,
      description: t("home.suggestions.strategy.description"),
      bgColor:
        "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#EAE8FF]/70 to-[100%]",
      decorativeGraphics: <img src={TrendPng} alt="Trend" />,
    },
    {
      id: "NewsAgent",
      title: t("home.suggestions.news.title"),
      icon: <SvgIcon name={NewsPush} />,
      description: t("home.suggestions.news.description"),
      bgColor:
        "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#FFE7FD]/70 to-[100%]",
      decorativeGraphics: <img src={MessageGroupPng} alt="MessageGroup" />,
    },
  ];

  return (
    <div className="flex h-full min-w-[800px] flex-col gap-3">
      {allPollTaskList && allPollTaskList.length > 0 ? (
        <section className="flex w-full flex-1 flex-col items-center justify-between gap-4">
          <TradingViewTickerTape
            symbols={INDEX_SYMBOLS}
            locale={getTradingViewLocale(i18n.language)}
          />

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
          <TradingViewTickerTape
            symbols={INDEX_SYMBOLS}
            locale={getTradingViewLocale(i18n.language)}
          />

          <h1 className="mt-16 font-medium text-3xl text-gray-950">
            {t("home.hello")}
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
            suggestions={suggestions.map((suggestion) => ({
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
