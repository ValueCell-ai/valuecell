import type { FC } from "react";
import type { AgentComponentType } from "./agent";

export type BaseRendererProps = {
  content: string;
  onOpen?: (data: string) => void;
};

export type ReportRendererProps = BaseRendererProps & {
  isActive?: boolean;
};
export type SecFeedRendererProps = BaseRendererProps;
export type MarkdownRendererProps = BaseRendererProps;
export type ToolCallRendererProps = BaseRendererProps;
export type ModelTradeRendererProps = BaseRendererProps;
export type ModelTradeTableRendererProps = BaseRendererProps;
export type ChatConversationRendererProps = BaseRendererProps;

/**
 * Mapping from component type to its corresponding props type
 * @description This enables type-safe renderer props based on component type
 */
export type RendererPropsMap = {
  sec_feed: SecFeedRendererProps;
  report: ReportRendererProps;
  markdown: MarkdownRendererProps;
  tool_call: ToolCallRendererProps;
  filtered_line_chart: ModelTradeRendererProps;
  filtered_card_push_notification: ModelTradeTableRendererProps;
  subagent_conversation: ChatConversationRendererProps;
};

/**
 * Generic renderer component type
 * @template T - The component type
 * @description Type-safe renderer component that accepts correct props based on component type
 */
export type RendererComponent<T extends AgentComponentType> = FC<
  RendererPropsMap[T]
>;
