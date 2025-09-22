import { ArrowUp, MessageCircle, Settings } from "lucide-react";
import { useRef, useState } from "react";
import { Navigate, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import ScrollTextarea, {
  type ScrollTextareaRef,
} from "@/components/valuecell/scroll/scroll-textarea";
import { cn } from "@/lib/utils";
import { agentData } from "@/mock/agent-data";
import type { Route } from "./+types/chat";

const ChatBackground = () => {
  return (
    <div className="-z-10 absolute inset-0 overflow-hidden opacity-30">
      {[
        {
          position: "left-0",
          size: "h-80 w-96",
          colors: "from-orange-200 to-orange-300",
        },
        {
          position: "left-56",
          size: "h-80 w-96",
          colors: "from-yellow-200 to-yellow-300",
        },
        {
          position: "left-96",
          size: "h-72 w-72",
          colors: "from-green-200 to-green-300",
        },
        {
          position: "right-56",
          size: "h-80 w-96",
          colors: "from-blue-200 to-blue-300",
        },
        {
          position: "right-0",
          size: "h-72 w-72",
          colors: "from-purple-200 to-purple-300",
        },
      ].map((blur, index) => (
        <div
          key={`${blur.position}-${index}`}
          className={`absolute top-1/2 ${blur.position} ${blur.size} -translate-y-1/2 transform`}
        >
          <div
            className={`h-full w-full rounded-full bg-gradient-to-br ${blur.colors} blur-[100px]`}
          />
        </div>
      ))}
    </div>
  );
};

export default function AgentChat() {
  const { agentId } = useParams<Route.LoaderArgs["params"]>();
  const textareaRef = useRef<ScrollTextareaRef>(null);
  const [inputValue, setInputValue] = useState("");

  const agent = agentData[agentId ?? ""];
  if (!agent) return <Navigate to="/" replace />;

  // Agent skills/tags
  const agentSkills = [
    "Hong Kong stocks",
    "US stocks",
    "Predictive analysis",
    "Stock selection",
  ];

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      // 这里处理发送消息的逻辑
      console.log("Sending message:", inputValue);
      setInputValue(""); // 清空输入
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header with agent info and actions */}
      <header className="flex items-center justify-between border-gray-100 border-b p-6">
        <div className="flex items-center gap-4">
          {/* Agent Avatar */}
          <div className="relative size-12">
            <div className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg" />
            <div className="absolute inset-0.5 flex items-center justify-center rounded-full bg-white">
              <span className="font-semibold text-gray-700 text-sm">AI</span>
            </div>
          </div>

          {/* Agent Info */}
          <div className="flex flex-col gap-1">
            <h1 className="font-semibold text-gray-950 text-lg">
              AI Hedge Fund Agent
            </h1>
            <div className="flex items-center gap-2">
              {agentSkills.slice(0, 2).map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 font-medium text-blue-700 text-xs"
                >
                  {skill}
                </span>
              ))}
              {agentSkills.length > 2 && (
                <span className="text-gray-500 text-xs">
                  +{agentSkills.length - 2} more
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="size-9 rounded-lg hover:bg-gray-100"
          >
            <MessageCircle size={18} className="text-gray-600" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-9 rounded-lg hover:bg-gray-100"
          >
            <Settings size={18} className="text-gray-600" />
          </Button>
        </div>
      </header>

      {/* Main content area with background effects */}
      <main className="relative flex flex-1">
        {/* Background blur effects */}
        <ChatBackground />

        {/* Welcome content */}
        <div className="flex flex-1 flex-col items-center justify-center gap-4">
          <h1 className="text-center font-semibold text-2xl text-gray-950 leading-12">
            Welcome to AI hedge fund agent！
          </h1>

          {/* Input card */}
          <div
            className={cn(
              "flex w-2/3 min-w-[600px] flex-col gap-2 rounded-2xl bg-white p-4",
              "border border-gray-200 shadow-[0px_4px_20px_8px_rgba(17,17,17,0.04)]",
              "focus-within:border-gray-300 focus-within:shadow-[0px_4px_20px_8px_rgba(17,17,17,0.08)]",
            )}
          >
            <ScrollTextarea
              ref={textareaRef}
              value={inputValue}
              onInput={handleInputChange}
              placeholder="You can inquire and analyze the trend of NVIDIA in the next three months"
              maxHeight={120}
              minHeight={24}
            />
            <Button
              size="icon"
              className="size-8 cursor-pointer self-end rounded-full"
              onClick={handleSendMessage}
            >
              <ArrowUp size={16} className="text-white" />
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
