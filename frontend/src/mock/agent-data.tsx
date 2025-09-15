import {
  BarChart3,
  Brain,
  Briefcase,
  Calendar,
  DollarSign,
  Newspaper,
  Shield,
  Target,
  TrendingUp,
  User,
} from "lucide-react";
import type { AgentRecommendation } from "@/app/_home/components/agent-recommend-list";
import type { AgentSuggestion } from "@/app/_home/components/agent-suggestions-list";

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
    id: "1",
    title: "Stock selection",
    icon: <TrendingUp size={16} className="text-gray-500" />,
    avatars: [
      <UserAvatar key="1" bgColor="#3B82F6" text="A" />,
      <UserAvatar key="2" bgColor="#10B981" text="B" />,
    ],
  },
  {
    id: "2",
    title: "Stock analysis",
    icon: <BarChart3 size={16} className="text-gray-500" />,
    avatars: [
      <UserAvatar key="1" bgColor="#8B5CF6" text="C" />,
      <UserAvatar key="2" bgColor="#F59E0B" text="D" />,
    ],
  },
  {
    id: "3",
    title: "Trading strategies",
    icon: <Target size={16} className="text-gray-500" />,
    avatars: [
      <UserAvatar key="1" bgColor="#EF4444" text="E" />,
      <UserAvatar key="2" bgColor="#06B6D4" text="F" />,
    ],
  },
  {
    id: "4",
    title: "Event interpretation",
    icon: <Calendar size={16} className="text-gray-500" />,
    avatars: [
      <UserAvatar key="1" bgColor="#84CC16" text="G" />,
      <UserAvatar key="2" bgColor="#F97316" text="H" />,
    ],
  },
  {
    id: "5",
    title: "News push",
    icon: <Newspaper size={16} className="text-gray-500" />,
    avatars: [
      <UserAvatar key="1" bgColor="#EC4899" text="I" />,
      <UserAvatar key="2" bgColor="#6366F1" text="J" />,
    ],
  },
  {
    id: "6",
    title: "Risk management",
    icon: <Shield size={16} className="text-gray-500" />,
    avatars: [
      <UserAvatar key="1" bgColor="#14B8A6" text="K" />,
      <UserAvatar key="2" bgColor="#F43F5E" text="L" />,
    ],
  },
];

// Agent recommendations for horizontal marquee carousel
export const agentRecommendations: AgentRecommendation[] = [
  {
    id: "recommend-1",
    title: "Tu share Agent",
    icon: (
      <div className="flex size-8 items-center justify-center rounded-full bg-[#A7BAFE]">
        <User size={16} className="text-white" />
      </div>
    ),
  },
  {
    id: "recommend-2",
    title: "Stock selection",
    icon: (
      <div className="flex size-8 items-center justify-center rounded-full bg-[#D9D9D9]">
        <TrendingUp size={16} className="text-gray-600" />
      </div>
    ),
  },
  {
    id: "recommend-3",
    title: "Peter Lynch agent",
    icon: (
      <div className="flex size-8 items-center justify-center rounded-full bg-[#3C3D44]">
        <Brain size={16} className="text-white" />
      </div>
    ),
  },
  {
    id: "recommend-4",
    title: "Graham Agent",
    icon: (
      <div className="flex size-8 items-center justify-center rounded-full bg-[#D9D9D9]">
        <Briefcase size={16} className="text-gray-600" />
      </div>
    ),
  },
  {
    id: "recommend-5",
    title: "巴菲特投资Agent",
    icon: (
      <div className="flex size-8 items-center justify-center rounded-full bg-[#D9D9D9]">
        <DollarSign size={16} className="text-gray-600" />
      </div>
    ),
  },
  {
    id: "recommend-6",
    title: "Geweidong Agent",
    icon: (
      <div className="flex size-8 items-center justify-center rounded-full bg-[#3C3D44]">
        <User size={16} className="text-white" />
      </div>
    ),
  },
  {
    id: "recommend-7",
    title: "AI Hedge fund",
    icon: (
      <div className="flex size-8 items-center justify-center rounded-full bg-[#D9D9D9]">
        <BarChart3 size={16} className="text-gray-600" />
      </div>
    ),
  },
  {
    id: "recommend-8",
    title: "Event interpretation",
    icon: (
      <div className="flex size-8 items-center justify-center rounded-full bg-[#D9D9D9]">
        <Calendar size={16} className="text-gray-600" />
      </div>
    ),
  },
];
