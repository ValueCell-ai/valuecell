import { BarChart3, Target, TrendingUp } from "lucide-react";
import type { AgentSuggestion } from "@/app/home/components/agent-suggestions-list";
import { IconGroupPng, MessageGroupPng, TrendPng } from "@/assets/png";

export const agentSuggestions: AgentSuggestion[] = [
  {
    id: "SecAgent",
    title: "Sec selection",
    icon: <TrendingUp size={16} className="text-gray-500" />,
    description: "Sec selection 11111111111111111111",
    bgColor:
      "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#E7EFFF]/70 to-[100%]",
    decorativeGraphics: <img src={TrendPng} alt="Trend" />,
  },
  {
    id: "WarrenBuffettAgent",
    title: "Investment master",
    icon: <BarChart3 size={16} className="text-gray-500" />,
    description: "Investment master",
    bgColor:
      "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#EAE8FF]/70 to-[100%]",
    decorativeGraphics: <img src={IconGroupPng} alt="IconGroup" />,
  },
  {
    id: "TradingAgentsAdapter",
    title: "Trading strategies",
    icon: <Target size={16} className="text-gray-500" />,
    description: "Trading strategies",
    bgColor:
      "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#FFE7FD]/70 to-[100%]",
    decorativeGraphics: <img src={MessageGroupPng} alt="MessageGroup" />,
  },
];
