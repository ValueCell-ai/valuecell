import {
  type FC,
  type HTMLAttributes,
  memo,
  type ReactNode,
  useMemo,
} from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useLocation } from "react-router";
import { useGetAgentList } from "@/api/agent";
import {
  Conversation,
  Logo,
  Market,
  Ranking,
  Setting,
  StrategyAgent,
} from "@/assets/svg";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import AppConversationSheet from "@/components/valuecell/app/app-conversation-sheet";
import AgentAvatar from "@/components/valuecell/icon/agent-avatar";
import SvgIcon from "@/components/valuecell/icon/svg-icon";
import { cn } from "@/lib/utils";

interface SidebarItemProps extends HTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
  type?: "button" | "agent";
}

interface SidebarProps {
  children: ReactNode;
  className?: string;
}

interface SidebarHeaderProps {
  children: ReactNode;
  className?: string;
}

interface SidebarContentProps {
  children: ReactNode;
  className?: string;
}

interface SidebarFooterProps {
  children: ReactNode;
  className?: string;
}

interface SidebarMenuProps {
  children: ReactNode;
  className?: string;
}

const Sidebar: FC<SidebarProps> = ({ children, className }) => {
  return (
    <div className={cn("flex w-16 flex-col items-center bg-muted", className)}>
      {children}
    </div>
  );
};

const SidebarHeader: FC<SidebarHeaderProps> = ({ children, className }) => {
  return <div className={cn("px-4 pt-5 pb-3", className)}>{children}</div>;
};

const SidebarContent: FC<SidebarContentProps> = ({ children, className }) => {
  return (
    <div className={cn("flex w-full flex-1 flex-col gap-3", className)}>
      {children}
    </div>
  );
};

const SidebarFooter: FC<SidebarFooterProps> = ({ children, className }) => {
  return (
    <div className={cn("flex flex-col gap-3 pb-4", className)}>{children}</div>
  );
};

const SidebarMenu: FC<SidebarMenuProps> = ({ children, className }) => {
  return (
    <div className={cn("flex flex-col items-center gap-3", className)}>
      {children}
    </div>
  );
};

const SidebarMenuItem: FC<SidebarItemProps> = ({
  children,
  onClick,
  className,
  type = "button",
  ...props
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "box-border flex size-10 items-center justify-center rounded-full",
        "cursor-pointer transition-all",
        type === "button" && [
          "bg-muted p-3 text-muted-foreground",
          "hover:data-[active=false]:bg-accent hover:data-[active=false]:text-accent-foreground",
          "data-[active=true]:bg-primary data-[active=true]:text-primary-foreground",
        ],
        type === "agent" && [
          "box-border border border-border bg-background",
          "hover:data-[active=false]:border-ring/50",
          "data-[active=true]:border-primary data-[active=true]:shadow-[0_4px_12px_0_rgba(0,0,0,0.25)]",
        ],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
};

const AppSidebar: FC = () => {
  const { t } = useTranslation();
  const pathArray = useLocation().pathname.split("/");

  const prefix = useMemo(() => {
    const subPath = pathArray[1] ?? "";
    switch (subPath) {
      case "agent":
        return `/${subPath}/${pathArray[2]}`;
      default:
        return `/${subPath}`;
    }
  }, [pathArray]);

  const navItems = useMemo(() => {
    return {
      home: [
        {
          id: "home",
          icon: Logo,
          label: t("nav.home"),
          to: "/home",
        },
        {
          id: "strategy",
          icon: StrategyAgent,
          label: t("nav.strategy"),
          to: "/agent/StrategyAgent",
        },
        {
          id: "ranking",
          icon: Ranking,
          label: t("nav.ranking"),
          to: "/ranking",
        },
        {
          id: "market",
          icon: Market,
          label: t("nav.market"),
          to: "/market",
        },
      ],
      config: [
        {
          id: "setting",
          icon: Setting,
          label: t("nav.setting"),
          to: "/setting",
        },
      ],
    };
  }, [t]);

  const { data: agentList } = useGetAgentList({ enabled_only: "true" });
  const agentItems = useMemo(() => {
    return agentList?.map((agent) => ({
      id: agent.agent_name,
      label: agent.display_name,
      to: `/agent/${agent.agent_name}`,
    }));
  }, [agentList]);

  // verify the button is active
  const verifyActive = (to: string) => prefix === to;

  return (
    <Sidebar>
      <SidebarHeader>
        <SidebarMenu>
          {navItems.home.map((item) => {
            return (
              <NavLink key={item.id} to={item.to}>
                <SidebarMenuItem
                  aria-label={item.label}
                  data-active={verifyActive(item.to)}
                  className="p-2"
                >
                  <SvgIcon name={item.icon} />
                </SidebarMenuItem>
              </NavLink>
            );
          })}

          <AppConversationSheet>
            <SidebarMenuItem className="cursor-pointer p-2">
              <SvgIcon name={Conversation} className="size-6" />
            </SidebarMenuItem>
          </AppConversationSheet>
        </SidebarMenu>
      </SidebarHeader>

      <Separator className="w-10! bg-border" />

      <SidebarContent>
        <SidebarMenu className="py-3">
          {agentItems?.map((item) => {
            return (
              <NavLink key={item.id} to={item.to}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <SidebarMenuItem
                      type="agent"
                      aria-label={item.label}
                      data-active={verifyActive(item.to)}
                    >
                      <AgentAvatar agentName={item.id} />
                    </SidebarMenuItem>
                  </TooltipTrigger>
                  <TooltipContent side="right">{item.label}</TooltipContent>
                </Tooltip>
              </NavLink>
            );
          })}
        </SidebarMenu>
      </SidebarContent>

      <SidebarFooter className="mt-auto pt-3">
        <SidebarMenu>
          {navItems.config.map((item) => {
            return (
              <NavLink key={item.id} to={item.to}>
                <SidebarMenuItem
                  aria-label={item.label}
                  data-active={verifyActive(item.to)}
                  className="p-2"
                >
                  <SvgIcon name={item.icon} />
                </SidebarMenuItem>
              </NavLink>
            );
          })}
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
};

export default memo(AppSidebar);
