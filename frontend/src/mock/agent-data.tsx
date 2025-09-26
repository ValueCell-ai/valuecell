import { BarChart3, Target, TrendingUp } from "lucide-react";
import type { AgentSuggestion } from "@/app/home/components/agent-suggestions-list";

const UserAvatar = ({ bgColor, text }: { bgColor: string; text: string }) => (
  <div
    className="flex h-full w-full items-center justify-center rounded-full font-medium text-white text-xs"
    style={{ backgroundColor: bgColor }}
  >
    {text}
  </div>
);

export const agentSuggestions: AgentSuggestion[] = [
  {
    id: "SecAgent",
    title: "Sec selection",
    icon: <TrendingUp size={16} className="text-gray-500" />,
    // avatars: [
    //   <UserAvatar key="1" bgColor="#3B82F6" text="A" />,
    //   <UserAvatar key="2" bgColor="#10B981" text="B" />,
    // ],
  },
  {
    id: "WarrenBuffettAgent",
    title: "Investment master",
    icon: <BarChart3 size={16} className="text-gray-500" />,
    // avatars: [
    //   <UserAvatar key="1" bgColor="#8B5CF6" text="C" />,
    //   <UserAvatar key="2" bgColor="#F59E0B" text="D" />,
    // ],
  },
  {
    id: "TradingAgentsAdapter",
    title: "Trading strategies",
    icon: <Target size={16} className="text-gray-500" />,
    // avatars: [
    //   <UserAvatar key="1" bgColor="#EF4444" text="E" />,
    //   <UserAvatar key="2" bgColor="#06B6D4" text="F" />,
    // ],
  },
  // {
  //   id: "4",
  //   title: "Event interpretation",
  //   icon: <Calendar size={16} className="text-gray-500" />,
  //   avatars: [
  //     <UserAvatar key="1" bgColor="#84CC16" text="G" />,
  //     <UserAvatar key="2" bgColor="#F97316" text="H" />,
  //   ],
  // },
  // {
  //   id: "5",
  //   title: "News push",
  //   icon: <Newspaper size={16} className="text-gray-500" />,
  //   avatars: [
  //     <UserAvatar key="1" bgColor="#EC4899" text="I" />,
  //     <UserAvatar key="2" bgColor="#6366F1" text="J" />,
  //   ],
  // },
  // {
  //   id: "6",
  //   title: "Risk management",
  //   icon: <Shield size={16} className="text-gray-500" />,
  //   avatars: [
  //     <UserAvatar key="1" bgColor="#14B8A6" text="K" />,
  //     <UserAvatar key="2" bgColor="#F43F5E" text="L" />,
  //   ],
  // },
];
