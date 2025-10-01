import { BarChart3, Target, TrendingUp } from "lucide-react";
import type { AgentSuggestion } from "@/app/home/components/agent-suggestions-list";
import { IconGroupPng, MessageGroupPng, TrendPng } from "@/assets/png";

export const agentSuggestions: AgentSuggestion[] = [
  {
    id: "TradingAgents",
    title: "Research Report",
    icon: <TrendingUp size={16} className="text-gray-500" />,
    description: "Diversified in-depth analysis reports",
    bgColor:
      "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#E7EFFF]/70 to-[100%]",
    decorativeGraphics: <img src={TrendPng} alt="Trend" />,
  },
  {
    id: "WarrenBuffettAgent",
    title: "Investment Master",
    icon: <BarChart3 size={16} className="text-gray-500" />,
    description: "Investment Master Research Analysis",
    bgColor:
      "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#EAE8FF]/70 to-[100%]",
    decorativeGraphics: <img src={IconGroupPng} alt="IconGroup" />,
  },
  {
    id: "SECAgent",
    title: "Selection SEC",
    icon: <Target size={16} className="text-gray-500" />,
    description: "SEC Stock Information Query",
    bgColor:
      "bg-gradient-to-r from-[#FFFFFF]/70 from-[5.05%] to-[#FFE7FD]/70 to-[100%]",
    decorativeGraphics: <img src={MessageGroupPng} alt="MessageGroup" />,
  },
];
