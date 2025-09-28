import type { FC } from "react";
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
  MarkdownRenderer,
  SecFeedRenderer,
} from "@/components/valuecell/renderer";
import type { AgentComponentType } from "@/types/agent";

// component_type to section type
export const AGENT_SECTION_COMPONENT_TYPE = ["sec_feed"] as const;

// agent component type
export const AGENT_COMPONENT_TYPE = [
  "markdown",
  "tool_call",
  ...AGENT_SECTION_COMPONENT_TYPE,
] as const;

export const COMPONENT_RENDERER_MAP: Record<
  AgentComponentType,
  FC<{ content: string }>
> = {
  sec_feed: SecFeedRenderer,
  markdown: MarkdownRenderer,
  tool_call: MarkdownRenderer,
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
  TradingAgentsAdapter: PortfolioManagerPng,
  SECAgent: SecAgentPng,
};
