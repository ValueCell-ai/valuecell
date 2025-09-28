import { BarChart3, Target, TrendingUp } from "lucide-react";
import type { AgentSuggestion } from "@/app/home/components/agent-suggestions-list";
import { IconGroupPng, MessageGroupPng, TrendPng } from "@/assets/png";

export const agentSuggestions: AgentSuggestion[] = [
  {
    id: "SecAgent",
    title: "Selection sec",
    icon: <TrendingUp size={16} className="text-gray-500" />,
    description:
      "Stock selection、Find your next winning stock with data-driven insights.",
    bgColor:
      "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#E7EFFF]/70 to-[100%]",
    decorativeGraphics: <img src={TrendPng} alt="Trend" />,
  },
  {
    id: "WarrenBuffettAgent",
    title: "Investment master",
    icon: <BarChart3 size={16} className="text-gray-500" />,
    description:
      "Stock analysis、In-depth analysis and reports on stocks, instantly.",
    bgColor:
      "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#EAE8FF]/70 to-[100%]",
    decorativeGraphics: <img src={IconGroupPng} alt="IconGroup" />,
  },
  {
    id: "TradingAgentsAdapter",
    title: "Research report",
    icon: <Target size={16} className="text-gray-500" />,
    description: "News push、Pushing personalized news that matters",
    bgColor:
      "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#FFE7FD]/70 to-[100%]",
    decorativeGraphics: <img src={MessageGroupPng} alt="MessageGroup" />,
  },
];
