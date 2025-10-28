import { ArrowRight, X } from "lucide-react";
import { Link } from "react-router";
import { useEnableAgent, useGetAgentInfo } from "@/api/agent";
import { Button } from "@/components/ui/button";
import AgentAvatar from "@/components/valuecell/agent-avatar";
import { MarkdownRenderer } from "@/components/valuecell/renderer";
import { useEffect } from "react";

interface AgentConfigDialogProps {
    agentName: string;
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
}

export function AgentConfigDialog({ agentName, isOpen, onOpenChange }: AgentConfigDialogProps) {
    const { data: agent, isLoading: isLoadingAgent } = useGetAgentInfo({
        agentName: agentName,
    });
    const { mutateAsync } = useEnableAgent();

    const handleEnableAgent = async () => {
        await mutateAsync({
            agentName: agentName,
            enabled: !agent?.enabled,
        });
    };

    const handleEnableAndChat = async () => {
        await handleEnableAgent();
        onOpenChange(false);
    };

    // Handle escape key
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                onOpenChange(false);
            }
        };

        if (isOpen) {
            document.addEventListener("keydown", handleEscape);
            // Prevent body scroll when dialog is open
            document.body.style.overflow = "hidden";
        }

        return () => {
            document.removeEventListener("keydown", handleEscape);
            document.body.style.overflow = "unset";
        };
    }, [isOpen, onOpenChange]);

    if (!isOpen || (!agent && !isLoadingAgent)) return null;

    return (
        <>
            {/* Backdrop */}
            <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm animate-in fade-in-0" onClick={() => onOpenChange(false)} />

            {/* Dialog */}
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => onOpenChange(false)}>
                <div
                    className="relative h-[25vh] w-[25vw] rounded-xl bg-white shadow-2xl animate-in fade-in-0 zoom-in-95"
                    onClick={(e) => e.stopPropagation()}>
                    {/* Custom close button */}
                    <button
                        onClick={() => onOpenChange(false)}
                        className="absolute right-3 top-3 z-10 rounded-full p-1.5 hover:bg-gray-100 transition-colors">
                        <X className="h-6 w-6 cursor-pointer" />
                    </button>

                    {/* Main container */}
                    <div className="flex h-full flex-col overflow-hidden rounded-xl">
                        {/* Header Section */}
                        <div className="border-b bg-linear-to-r from-gray-50 to-white px-6 py-4">
                            {/* Agent Info */}
                            <div className="flex items-center space-x-4">
                                <AgentAvatar agentName={agentName} className="h-18 w-18 rounded-lg" />

                                <div className="flex-1">
                                    <h1 className="text-2xl font-bold text-gray-900 cursor-default">{agent?.display_name}</h1>

                                    {/* Tags */}
                                    <div className="flex flex-wrap gap-1 mt-2">
                                        {agent?.agent_metadata.tags.map((tag) => (
                                            <span
                                                key={tag}
                                                className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 cursor-default">
                                                {tag}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Content Section */}
                        <div className="flex-1 overflow-hidden bg-white">
                            <div className="h-full overflow-y-auto px-6 py-3">
                                <div className="prose prose-sm prose-gray max-w-none">
                                    <MarkdownRenderer content={agent?.description ?? ""} />
                                </div>
                            </div>
                        </div>

                        {/* Bottom Action Buttons */}
                        <div className="border-t bg-gray-50 px-6 py-3">
                            <div className="flex items-center justify-end space-x-2">
                                {agent?.enabled ? (
                                    <>
                                        {agentName !== "ValueCellAgent" && (
                                            <Button
                                                variant="outline"
                                                onClick={handleEnableAgent}
                                                className="px-5 py-3 rounded-md font-semibold">
                                                Disable
                                            </Button>
                                        )}
                                        <Link
                                            className="flex items-center gap-2 rounded-md bg-black px-5 py-1.5 font-semibold text-base text-white hover:bg-black/80"
                                            to={`/agent/${agentName}`}>
                                            Chat <ArrowRight size={16} />
                                        </Link>
                                    </>
                                ) : (
                                    <Link
                                        className="flex items-center gap-2 rounded-md bg-black px-5 py-3 font-semibold text-base text-white hover:bg-black/80"
                                        to={`/agent/${agentName}`}
                                        onClick={handleEnableAndChat}>
                                        Collect and chat
                                        <ArrowRight size={16} />
                                    </Link>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}
