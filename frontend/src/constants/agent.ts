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
  NewPushAgentPng,
  PeterLynchPng,
  PhilFisherPng,
  PortfolioManagerPng,
  RakeshJhunjhunwalaPng,
  ResearchAgentPng,
  SecAgentPng,
  StanleyDruckenmillerPng,
  StrategyAgentPng,
  TechnicalAgencyPng,
  ValuationAgencyPng,
  ValueCellAgentPng,
  WarrenBuffettPng,
} from "@/assets/png";
import {
  ChatConversationRenderer,
  MarkdownRenderer,
  ReportRenderer,
  ScheduledTaskControllerRenderer,
  ScheduledTaskRenderer,
  ToolCallRenderer,
} from "@/components/valuecell/renderer";
import { TimeUtils } from "@/lib/time";
import type { AgentComponentType, AgentInfo } from "@/types/agent";
import type { RendererComponent } from "@/types/renderer";

// component_type to section type
export const AGENT_SECTION_COMPONENT_TYPE = ["scheduled_task_result"] as const;

// multi section component type
export const AGENT_MULTI_SECTION_COMPONENT_TYPE = ["report"] as const;

// agent component type
export const AGENT_COMPONENT_TYPE = [
  "markdown",
  "tool_call",
  "subagent_conversation",
  "scheduled_task_controller",
  ...AGENT_SECTION_COMPONENT_TYPE,
  ...AGENT_MULTI_SECTION_COMPONENT_TYPE,
] as const;

/**
 * Component renderer mapping with automatic type inference
 */
export const COMPONENT_RENDERER_MAP: {
  [K in AgentComponentType]: RendererComponent<K>;
} = {
  scheduled_task_result: ScheduledTaskRenderer,
  scheduled_task_controller: ScheduledTaskControllerRenderer,
  report: ReportRenderer,
  markdown: MarkdownRenderer,
  tool_call: ToolCallRenderer,
  subagent_conversation: ChatConversationRenderer,
};

export const AGENT_AVATAR_MAP: Record<string, string> = {
  // Investment Masters
  ResearchAgent: ResearchAgentPng,
  StrategyAgent: StrategyAgentPng,
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
  ValueCellAgent: ValueCellAgentPng,

  // Analyst Agents
  FundamentalsAnalystAgent: FundamentalProxyPng,
  TechnicalAnalystAgent: TechnicalAgencyPng,
  ValuationAnalystAgent: ValuationAgencyPng,
  SentimentAnalystAgent: EmotionalAgencyPng,

  // System Agents
  TradingAgents: PortfolioManagerPng,
  SECAgent: SecAgentPng,
  NewsAgent: NewPushAgentPng,
};

export const VALUECELL_AGENT: AgentInfo = {
  agent_name: "ValueCellAgent",
  display_name: "ValueCell Agent",
  enabled: true,
  description:
    "ValueCell Agent is a super-agent that can help you manage different agents and tasks",
  created_at: TimeUtils.nowUTC().toISOString(),
  updated_at: TimeUtils.nowUTC().toISOString(),
  agent_metadata: {
    version: "1.0.0",
    author: "ValueCell",
    tags: ["valuecell", "super-agent"],
  },
};

// Trading symbols options
export const TRADING_SYMBOLS: string[] = [
  "BTC/USDT",
  "ETH/USDT",
  "SOL/USDT",
  "DOGE/USDT",
  "XRP/USDT",
];
