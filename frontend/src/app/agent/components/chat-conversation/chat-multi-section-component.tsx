import { type FC, memo } from "react";
import BackButton from "@/components/valuecell/button/back-button";
import { MarkdownRenderer } from "@/components/valuecell/renderer";
import { useMultiSection } from "@/provider/multi-section-provider";
import type { MultiSectionComponentType } from "@/types/agent";

// define different component types and their specific rendering components
const ReportComponent: FC<{ data: string }> = ({ data }) => {
  const { closeSection } = useMultiSection();

  return (
    <>
      <BackButton className="mb-3" onClick={closeSection} />
      <MarkdownRenderer content={data} />
    </>
  );
};

const MULTI_SECTION_COMPONENT_MAP: Record<
  MultiSectionComponentType,
  FC<{ data: string }>
> = {
  report: ReportComponent,
};

interface ChatMultiSectionComponentProps {
  componentType: MultiSectionComponentType;
  data: string;
}

const ChatMultiSectionComponent: FC<ChatMultiSectionComponentProps> = ({
  componentType,
  data,
}) => {
  const Component = MULTI_SECTION_COMPONENT_MAP[componentType];
  return <Component data={data} />;
};

export default memo(ChatMultiSectionComponent);
