import {
  AswathDamodaranPng,
  BenGrahamPng,
  BillAckmanPng,
  CathieWoodPng,
  CharlieMungerPng,
  EmotionalAgencyPng,
  FundamentalProxyPng,
  MichaelBurryPng,
  MohnishPabraiPng,
  PeterLynchPng,
  PhilFisherPng,
  PortfolioManagerPng,
  RakeshJhunjhunwalaPng,
  SecAgentPng,
  StanleyDruckenmillerPng,
  TechnicalAgencyPng,
  ValuationAgencyPng,
  WarrenBuffettPng,
} from "@/assets/png";
import {
  ChatConversationRenderer,
  MarkdownRenderer,
  ModelTradeRenderer,
  ModelTradeTableRenderer,
  ReportRenderer,
  SecFeedRenderer,
  ToolCallRenderer,
} from "@/components/valuecell/renderer";
import type { AgentComponentType, AgentInfo } from "@/types/agent";
import type { RendererComponent } from "@/types/renderer";

// component_type to section type
export const AGENT_SECTION_COMPONENT_TYPE = [
  "sec_feed",
  "filtered_line_chart",
  "filtered_card_push_notification",
] as const;

// multi section component type
export const AGENT_MULTI_SECTION_COMPONENT_TYPE = ["report"] as const;

// agent component type
export const AGENT_COMPONENT_TYPE = [
  "markdown",
  "tool_call",
  "subagent_conversation",
  ...AGENT_SECTION_COMPONENT_TYPE,
  ...AGENT_MULTI_SECTION_COMPONENT_TYPE,
] as const;

/**
 * Component renderer mapping with automatic type inference
 */
export const COMPONENT_RENDERER_MAP: {
  [K in AgentComponentType]: RendererComponent<K>;
} = {
  sec_feed: SecFeedRenderer,
  filtered_line_chart: ModelTradeRenderer,
  filtered_card_push_notification: ModelTradeTableRenderer,
  report: ReportRenderer,
  markdown: MarkdownRenderer,
  tool_call: ToolCallRenderer,
  subagent_conversation: ChatConversationRenderer,
};

export const AGENT_AVATAR_MAP: Record<string, string> = {
  // Investment Masters
  AswathDamodaranAgent: AswathDamodaranPng,
  BenGrahamAgent: BenGrahamPng,
  BillAckmanAgent: BillAckmanPng,
  CathieWoodAgent: CathieWoodPng,
  CharlieMungerAgent: CharlieMungerPng,
  MichaelBurryAgent: MichaelBurryPng,
  MohnishPabraiAgent: MohnishPabraiPng,
  PeterLynchAgent: PeterLynchPng,
  PhilFisherAgent: PhilFisherPng,
  RakeshJhunjhunwalaAgent: RakeshJhunjhunwalaPng,
  StanleyDruckenmillerAgent: StanleyDruckenmillerPng,
  WarrenBuffettAgent: WarrenBuffettPng,

  // Analyst Agents
  FundamentalsAnalystAgent: FundamentalProxyPng,
  TechnicalAnalystAgent: TechnicalAgencyPng,
  ValuationAnalystAgent: ValuationAgencyPng,
  SentimentAnalystAgent: EmotionalAgencyPng,

  // System Agents
  TradingAgents: PortfolioManagerPng,
  SECAgent: SecAgentPng,
};

export const VALUECELL_AGENT: AgentInfo = {
  agent_name: "ValueCellAgent",
  display_name: "ValueCell Agent",
  enabled: true,
  description:
    "ValueCell Agent is a super-agent that can help you manage different agents and tasks",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  agent_metadata: {
    version: "1.0.0",
    author: "ValueCell",
    tags: ["valuecell", "super-agent"],
  },
};
