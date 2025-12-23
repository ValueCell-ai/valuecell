import { FileText } from "lucide-react";
import type { FC } from "react";
import type { ChatItem } from "@/types/agent";

interface UnknownRendererProps {
  item: ChatItem;
  content: string;
}

const UnknownRenderer: FC<UnknownRendererProps> = ({ item, content }) => {
  return (
    <div>
      <div className="mt-3 rounded-lg border border-border bg-muted p-3">
        <div className="mb-2 flex items-center gap-2">
          <FileText size={16} className="text-primary" />
          <span className="font-medium text-foreground text-sm capitalize">
            {item.component_type} (Unknown Component Type)
          </span>
        </div>
        <div className="rounded bg-card p-3 text-foreground text-sm">
          <pre className="whitespace-pre-wrap font-mono text-xs">{content}</pre>
        </div>
      </div>
    </div>
  );
};

export default UnknownRenderer;
