import type { FC } from "react";
import type { AgentComponentType } from "./agent";

export type BaseRendererProps = {
  content: string;
  className?: string;
  onOpen?: (data: string) => void;
};

export type ReportRendererProps = BaseRendererProps & {
  isActive?: boolean;
};
export type ReasoningRendererProps = BaseRendererProps & {
  isComplete?: boolean;
};
export type ScheduledTaskRendererProps = BaseRendererProps;
export type ScheduledTaskControllerRendererProps = BaseRendererProps;
export type MarkdownRendererProps = BaseRendererProps;
export type ToolCallRendererProps = BaseRendererProps;
export type ChatConversationRendererProps = BaseRendererProps;

/**
 * Mapping from component type to its corresponding props type
 * @description This enables type-safe renderer props based on component type
 */
export type RendererPropsMap = {
  scheduled_task_result: ScheduledTaskRendererProps;
  scheduled_task_controller: ScheduledTaskControllerRendererProps;
  report: ReportRendererProps;
  reasoning: ReasoningRendererProps;
  markdown: MarkdownRendererProps;
  tool_call: ToolCallRendererProps;
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
