import { ArrowRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useParams } from "react-router";
import { useEnableAgent, useGetAgentInfo } from "@/api/agent";
import { Button } from "@/components/ui/button";
import BackButton from "@/components/valuecell/button/back-button";
import AgentAvatar from "@/components/valuecell/icon/agent-avatar";
import { MarkdownRenderer } from "@/components/valuecell/renderer";
import type { Route } from "./+types/config";

export default function AgentConfig() {
  const { t } = useTranslation();
  const { agentName } = useParams<Route.LoaderArgs["params"]>();
  const { data: agent, isLoading: isLoadingAgent } = useGetAgentInfo({
    agentName: agentName ?? "",
  });
  const { mutateAsync } = useEnableAgent();

  if (!agentName && !isLoadingAgent) return <Navigate to="/" replace />;

  const handleEnableAgent = async () => {
    await mutateAsync({
      agentName: agentName ?? "",
      enabled: !agent?.enabled,
    });
  };

  return (
    <div className="scroll-container flex flex-1 flex-col gap-4 p-8">
      <BackButton />

      {/* Agent info and configure button */}
      <div className="mb-6 flex items-center justify-between rounded-lg bg-muted px-4 py-8">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-4">
            <AgentAvatar agentName={agentName ?? ""} className="size-16" />
            <h1 className="font-semibold text-4xl text-foreground leading-9">
              {agent?.display_name}
            </h1>
          </div>
          <div className="flex gap-2">
            {agent?.agent_metadata.tags.map((tag) => (
              <span
                key={tag}
                className="text-nowrap rounded-md border border-border px-3 py-1 font-normal text-muted-foreground text-xs"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        {agent?.enabled ? (
          <div className="flex items-center gap-4">
            {agentName !== "ValueCellAgent" && (
              <Button variant="secondary" onClick={handleEnableAgent}>
                {t("agent.config.disable")}
              </Button>
            )}
            <Link
              className="flex items-center gap-2 rounded-md bg-primary px-5 py-1.5 font-semibold text-base text-primary-foreground hover:bg-primary/80"
              to={`/agent/${agentName}`}
            >
              {t("agent.config.chat")} <ArrowRight size={16} />
            </Link>
          </div>
        ) : (
          <Link
            className="flex items-center gap-2 rounded-md bg-primary px-5 py-3 font-semibold text-base text-primary-foreground hover:bg-primary/80"
            to={`/agent/${agentName}`}
            onClick={handleEnableAgent}
          >
            {t("agent.config.collectAndChat")}
            <ArrowRight size={16} />
          </Link>
        )}
      </div>

      <MarkdownRenderer content={agent?.description ?? ""} />
    </div>
  );
}
