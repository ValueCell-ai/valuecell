import { MoreVertical, Trash2 } from "lucide-react";
import type { FC, ReactNode } from "react";
import { NavLink, useNavigate, useSearchParams } from "react-router";
import {
  useDeleteConversation,
  useGetConversationList,
} from "@/api/conversation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import AgentAvatar from "./agent-avatar";
import ScrollContainer from "./scroll/scroll-container";

const AppConversationSheet: FC<{ children: ReactNode }> = ({ children }) => {
  const [searchParams] = useSearchParams();
  const currentConversationId = searchParams.get("id") ?? "";
  const navigate = useNavigate();

  const { data: conversations = [], isLoading } = useGetConversationList();
  const { mutateAsync: deleteConversation } = useDeleteConversation();

  return (
    <Sheet>
      <SheetTrigger asChild>{children}</SheetTrigger>

      <SheetContent side="left" className="w-[300px]">
        <SheetHeader>
          <SheetTitle>Conversation List</SheetTitle>
        </SheetHeader>

        <ScrollContainer className="w-full flex-1 px-4">
          <SidebarMenu className="gap-[5px]">
            {isLoading ? (
              <div className="px-2 py-4 text-center text-gray-400 text-sm">
                Loading...
              </div>
            ) : conversations.length === 0 ? (
              <div className="px-2 py-4 text-center text-gray-400 text-sm">
                No conversation yet
              </div>
            ) : (
              conversations.map((conversation) => {
                const isActive =
                  conversation.conversation_id === currentConversationId;
                return (
                  <SidebarMenuItem key={conversation.conversation_id}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      className="h-auto flex-col items-start gap-1 p-2"
                    >
                      <NavLink
                        to={`/agent/${conversation.agent_name}?id=${conversation.conversation_id}`}
                      >
                        <div className="flex w-full items-center gap-1">
                          <div className="size-5 shrink-0 overflow-hidden rounded-full">
                            <AgentAvatar agentName={conversation.agent_name} />
                          </div>
                          <span className="truncate font-normal text-sm leading-5">
                            {conversation.title}
                          </span>
                        </div>
                        <span className="w-full font-normal text-gray-400 text-xs leading-[18px]">
                          {TimeUtils.formatUTC(
                            conversation.update_time,
                            TIME_FORMATS.DATE,
                          )}
                        </span>
                      </NavLink>
                    </SidebarMenuButton>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <SidebarMenuAction showOnHover>
                          <MoreVertical />
                        </SidebarMenuAction>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent side="right" align="start">
                        <DropdownMenuItem
                          variant="destructive"
                          onClick={async (e) => {
                            e.stopPropagation();
                            await deleteConversation(
                              conversation.conversation_id,
                            );

                            if (
                              conversation.conversation_id ===
                              currentConversationId
                            ) {
                              navigate("/home");
                            }
                          }}
                        >
                          <Trash2 />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </SidebarMenuItem>
                );
              })
            )}
          </SidebarMenu>
        </ScrollContainer>
      </SheetContent>
      <SheetDescription></SheetDescription>
    </Sheet>
  );
};

export default AppConversationSheet;
