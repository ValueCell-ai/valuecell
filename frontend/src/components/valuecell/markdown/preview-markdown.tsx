import ReactMarkdown from "react-markdown";

interface PreviewMarkdownProps {
  content: string;
}

export default function PreviewMarkdown({ content }: PreviewMarkdownProps) {
  return (
    <div className="prose">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
