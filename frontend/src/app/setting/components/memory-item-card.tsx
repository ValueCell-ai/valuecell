import { MoreVertical, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
} from "@/components/ui/item";
import type { MemoryItem } from "@/types/setting";

interface MemoryItemCardProps {
  item: MemoryItem;
  onDelete?: (id: MemoryItem["id"]) => void;
}

export function MemoryItemCard({ item, onDelete }: MemoryItemCardProps) {
  return (
    <Item variant="outline" className="rounded-xl">
      <ItemContent>
        <ItemDescription className="line-clamp-none text-base text-gray-950">
          {item.content}
        </ItemDescription>
      </ItemContent>
      <ItemActions>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="size-8 shrink-0 hover:bg-gray-100"
            >
              <MoreVertical className="size-5 text-gray-950" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              variant="destructive"
              onClick={() => onDelete?.(item.id)}
            >
              <Trash2 className="size-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </ItemActions>
    </Item>
  );
}

export default MemoryItemCard;
