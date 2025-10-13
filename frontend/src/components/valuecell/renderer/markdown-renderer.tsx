import { type FC, memo } from "react";
import ReactMarkdown from "react-markdown";
import type { MarkdownRendererProps } from "@/types/renderer";

const MarkdownRenderer: FC<MarkdownRendererProps> = ({ content }) => {
  return (
    <div className="prose">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
};

export default memo(MarkdownRenderer);
