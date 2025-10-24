import type { FC } from "react";
import { NavLink, useSearchParams } from "react-router";
import { useGetConversationList } from "@/api/conversation";
import { Conversation } from "@/assets/svg";
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
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import AgentAvatar from "./agent-avatar";
import ScrollContainer from "./scroll/scroll-container";
import SvgIcon from "./svg-icon";

const AppConversationSheet: FC = () => {
  const [searchParams] = useSearchParams();
  const currentConversationId = searchParams.get("id") ?? "";

  // Fetch conversation list
  const { data: conversations = [], isLoading } = useGetConversationList();

  return (
    <Sheet>
      <SheetTrigger asChild>
        <button type="button" className="cursor-pointer text-black">
          <SvgIcon name={Conversation} className="size-5" />
        </button>
      </SheetTrigger>

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
