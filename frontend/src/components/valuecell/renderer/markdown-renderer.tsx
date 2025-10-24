import { type FC, memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { MarkdownRendererProps } from "@/types/renderer";

const MarkdownRenderer: FC<MarkdownRendererProps> = ({ content }) => {
  return (
    <div className="prose">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
};

export default memo(MarkdownRenderer);
