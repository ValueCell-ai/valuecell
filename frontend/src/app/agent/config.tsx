import { ArrowRight } from "lucide-react";
import { useNavigate, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import BackButton from "@/components/valuecell/button/back-button";
import ScrollContainer from "@/components/valuecell/scroll-container";

// Mock agent data - in real app this would come from API
const agentData = {
  "warren-buffett": {
    name: "Warren Buffett Agent",
    description:
      "Looking for high-quality companies at fair prices, with a focus on moats and long-term value.",
    avatar: (
      <div className="relative size-12">
        <div className="absolute inset-0 rounded-full bg-[#D9D9D9]" />
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-gray-300 to-gray-400" />
      </div>
    ),
    introduction:
      "This AI Agent is not a simple stock selection tool or market predictor, but a decision assistance system that deeply integrates Warren Buffett's core investment philosophy with modern artificial intelligence technology. Its mission is to help users think like Buffett and systematically identify and hold high-quality companies in the global capital market for the long term.",
    advantages: [
      "Focus on Intrinsic Value, Not Price Noise",
      "Learnability & Evolution",
      'Built-in Risk Management - "Margin of Safety"',
      "High-Probability Investing",
      "Long-Term Compounding Orientation",
    ],
  },
  "peter-lynch": {
    name: "Peter Lynch Agent",
    description: "Growth investing strategies and stock picking expertise.",
    avatar: (
      <div className="relative size-12">
        <div className="absolute inset-0 rounded-full bg-[#A7BAFE]" />
      </div>
    ),
    introduction:
      "This AI Agent embodies Peter Lynch's growth investing philosophy, focusing on companies with strong earnings growth and market opportunities.",
    advantages: [
      "Growth Stock Identification",
      "Market Trend Analysis",
      "Earnings Growth Focus",
      "Sector Rotation Strategies",
    ],
  },
};

export default function AgentConfig() {
  const { agentId } = useParams();
  const navigate = useNavigate();

  const agent = agentData[agentId as keyof typeof agentData];

  if (!agent) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#eef0f3]">
        <div className="rounded-[12px] bg-white p-8">
          <div className="text-center">
            <h1 className="mb-4 font-medium text-2xl text-black">
              Agent Not Found
            </h1>
            <p className="text-gray-600">
              The agent "{agentId}" does not exist.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const handleConfigure = () => {
    // In the future, this could navigate to a separate configuration page
    // For now, we'll just navigate to the chat page
    navigate(`/agent/${agentId}`);
  };

  return (
    <div className="flex flex-1 flex-col gap-8 overflow-hidden py-8">
      <BackButton className="mx-8" />

      {/* Agent info and configure button */}
      <div className="mb-10 flex justify-between px-8">
        <div className="flex flex-col gap-4">
          {agent.avatar}
          <div className="flex flex-col gap-2">
            <h1 className="font-semibold text-4xl leading-9">{agent.name}</h1>
            <p className="text-base text-neutral-500 leading-6">
              {agent.description}
            </p>
          </div>
        </div>

        <Button
          onClick={handleConfigure}
          className="cursor-pointer gap-2 rounded-md px-5 py-3 font-semibold text-base text-white"
        >
          Activate Chat
          <ArrowRight size={16} />
        </Button>
      </div>

      <ScrollContainer className="px-8">
        <div className="flex flex-col gap-10">
          {/* Introduction */}
          <div className="flex flex-col gap-[18px]">
            <h2 className="font-semibold text-base text-black">Introduction</h2>
            <p className="max-w-[1143px] text-[#5a5a5a] text-base leading-6">
              {agent.introduction}
            </p>
          </div>

          {/* Agent Advantages */}
          <div className="flex flex-col gap-4">
            <h2 className="font-semibold text-base text-black">
              Agent Advantage
            </h2>
            <div className="flex max-w-[469px] flex-col gap-1">
              {agent.advantages.map((advantage) => (
                <div key={advantage} className="flex items-start gap-2">
                  <div className="mt-3 h-1 w-1 shrink-0 rounded-full bg-[#5a5a5a]" />
                  <span className="text-[#5a5a5a] text-base leading-[29px]">
                    {advantage}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </ScrollContainer>
    </div>
  );
}
