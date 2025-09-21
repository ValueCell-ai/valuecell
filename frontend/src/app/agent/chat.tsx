import { ArrowUp, MessageCircle, Settings } from "lucide-react";
import { useRef } from "react";
import { Navigate, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import ScrollContainer from "@/components/valuecell/scroll-container";
import { agentData } from "@/mock/agent-data";
import type { Route } from "./+types/chat";

export default function AgentChat() {
  const { agentId } = useParams<Route.LoaderArgs["params"]>();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  if (!agentId) return <Navigate to="/" replace />;

  const agent = agentData[agentId];
  if (!agent) return <Navigate to="/" replace />;

  // Agent skills/tags
  const agentSkills = [
    "Hong Kong stocks",
    "US stocks",
    "Predictive analysis",
    "Stock selection",
  ];

  const handleSendMessage = () => {
    if (textareaRef.current?.value?.trim()) {
      textareaRef.current.value = "";
    }
  };

  return (
    <div className="flex size-full flex-col gap-2 rounded-tl-4 bg-white p-8">
      {/* Header with agent info and actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Agent Avatar */}
          <div className="relative size-14">
            <div className="absolute inset-0 rounded-full bg-white" />
            <div className="absolute inset-0 rounded-full bg-gradient-to-br from-gray-300 to-gray-400" />
          </div>

          {/* Agent Info */}
          <div className="flex flex-col gap-1.5">
            <p className="font-semibold text-base text-gray-950 leading-5.5">
              AI hedge fund agent
            </p>
            <div className="flex items-center gap-1">
              {agentSkills.map((skill) => (
                <div
                  key={skill}
                  className="whitespace-nowrap rounded-lg bg-gray-100 px-3 py-1 text-gray-700 text-xs"
                >
                  {skill}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2.5">
          <Button
            variant="secondary"
            size="icon"
            className="size-8 rounded-lg bg-gray-100"
          >
            <MessageCircle size={16} className="text-gray-600" />
          </Button>
          <Button
            variant="secondary"
            size="icon"
            className="size-8 rounded-lg bg-gray-100"
          >
            <Settings size={20} className="text-gray-600" />
          </Button>
        </div>
      </div>

      {/* Main content area with background effects */}
      <div className="relative flex flex-1 flex-col items-center justify-center pt-0 pb-10">
        {/* Background blur effects */}
        <div className="absolute inset-0 opacity-40">
          <div className="-translate-y-1/2 absolute top-1/2 left-0 h-[332px] w-[411px]">
            <div className="h-full w-full rounded-full bg-[#FFDFCD] blur-[150px]" />
          </div>
          <div className="-translate-y-1/2 absolute top-1/2 left-[229px] h-[332px] w-[411px]">
            <div className="h-full w-full rounded-full bg-[#FFF8D7] blur-[150px]" />
          </div>
          <div className="-translate-y-1/2 absolute top-1/2 left-[458px] h-[332px] w-[332px]">
            <div className="h-full w-full rounded-full bg-[#D3FFDA] blur-[150px]" />
          </div>
          <div className="-translate-y-1/2 absolute top-1/2 right-[243px] h-[332px] w-[411px]">
            <div className="h-full w-full rounded-full bg-[#DCE8FF] blur-[150px]" />
          </div>
          <div className="-translate-y-1/2 absolute top-1/2 right-0 h-[332px] w-[332px]">
            <div className="h-full w-full rounded-full bg-[#F1DCFF] blur-[150px]" />
          </div>
        </div>

        {/* Welcome content */}
        <div className="relative z-10 flex w-[800px] flex-col items-center gap-4">
          <div className="flex flex-col items-center gap-4">
            <h1 className="w-[523px] text-center font-semibold text-2xl text-gray-950 leading-12">
              Welcome to AI hedge fund agent！
            </h1>
          </div>

          {/* Input card */}
          <div className="relative w-full rounded-2xl border border-gray-200 bg-white p-4">
            {/* Shadow overlay */}
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 rounded-2xl border border-gray-200 border-solid"
              style={{ boxShadow: "0px 4px 20px 8px rgba(17, 17, 17, 0.04)" }}
            />

            <div className="flex w-full flex-col gap-2">
              <ScrollContainer className="max-h-[120px]">
                <textarea
                  ref={textareaRef}
                  placeholder="You can inquire and analyze the trend of NVIDIA in the next three months"
                  className="field-sizing-content w-full resize-none border-0 bg-transparent p-0 text-base leading-5.5 outline-none placeholder:text-gray-400"
                />
              </ScrollContainer>
              <Button
                size="icon"
                className="size-8 cursor-pointer self-end rounded-full"
                onClick={handleSendMessage}
              >
                <ArrowUp size={16} className="text-white" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
