import type { FC } from "react";
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
