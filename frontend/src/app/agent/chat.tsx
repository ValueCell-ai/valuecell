import { useParams } from "react-router";

export default function AgentChat() {
  const { agentId } = useParams();

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#eef0f3] p-4">
      <div className="w-full max-w-[1360px] rounded-[12px] bg-white shadow-lg">
        <div className="flex h-full flex-col p-8">
          <h1 className="font-medium text-3xl text-black leading-9">
            Chat with Agent: {agentId}
          </h1>
          <div className="mt-8 flex-1">
            {/* Chat interface will be implemented here */}
            <div className="flex h-full items-center justify-center text-gray-500">
              Chat interface coming soon...
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
