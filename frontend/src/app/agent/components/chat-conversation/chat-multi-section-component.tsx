import { parse } from "best-effort-json-parser";
import { type FC, memo } from "react";
import BackButton from "@/components/valuecell/button/back-button";
import { MarkdownRenderer } from "@/components/valuecell/renderer";
import { useMultiSection } from "@/provider/multi-section-provider";
import type { MultiSectionComponentType } from "@/types/agent";

// define different component types and their specific rendering components
const ReportComponent: FC<{ content: string }> = ({ content }) => {
  const { closeSection } = useMultiSection();
  const { title, data } = parse(content);

  return (
    <>
      <header className="mb-3 flex items-center gap-2">
        <BackButton onClick={closeSection} />
        <h4 className="font-semibold text-lg">{title}</h4>
      </header>
      <MarkdownRenderer content={data} />
    </>
  );
};

const MULTI_SECTION_COMPONENT_MAP: Record<
  MultiSectionComponentType,
  FC<{ content: string }>
> = {
  report: ReportComponent,
};

interface ChatMultiSectionComponentProps {
  componentType: MultiSectionComponentType;
  content: string;
}

const ChatMultiSectionComponent: FC<ChatMultiSectionComponentProps> = ({
  componentType,
  content,
}) => {
  const Component = MULTI_SECTION_COMPONENT_MAP[componentType];
  return <Component content={content} />;
};

export default memo(ChatMultiSectionComponent);
