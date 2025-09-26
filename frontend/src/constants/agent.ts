// component_type to section type
export const AGENT_SECTION_COMPONENT_TYPE = ["sec_feed"] as const;

// agent component type
export const AGENT_COMPONENT_TYPE = [
  "markdown",
  ...AGENT_SECTION_COMPONENT_TYPE,
] as const;
