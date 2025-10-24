import {
  type FC,
  type HTMLAttributes,
  memo,
  type ReactNode,
  useMemo,
} from "react";
import { NavLink, useLocation } from "react-router";
import { useGetAgentList } from "@/api/agent";
import { ChartBarVertical, Logo, Setting } from "@/assets/svg";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip";
import AgentAvatar from "./agent-avatar";
import ScrollContainer from "./scroll/scroll-container";
import SvgIcon from "./svg-icon";

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
    <div
      className={cn(
        "flex w-16 flex-col items-center bg-neutral-100",
        className,
      )}
    >
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
          "bg-neutral-200 p-3",
          "hover:data-[active=false]:bg-neutral-300",
          "data-[active=true]:bg-black data-[active=true]:text-white",
        ],
        type === "agent" && [
          "box-border border border-neutral-200 bg-white",
          "hover:data-[active=false]:border-neutral-300",
          "data-[active=true]:border-white data-[active=true]:shadow-[0_4px_12px_0_rgba(14,1,1,0.4)]",
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
          label: "Home",
          to: "/home",
        },
        {
          id: "market",
          icon: ChartBarVertical,
          label: "Market",
          to: "/market",
        },
      ],
      config: [
        {
          id: "setting",
          icon: Setting,
          label: "Setting",
          to: "/setting",
        },
      ],
    };
  }, []);

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
    <Sidebar className="bg-gray-100">
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
        </SidebarMenu>
      </SidebarHeader>

      <Separator className="w-10! bg-white" />

      <SidebarContent className="max-h-[calc(100vh-11rem)]">
        <ScrollContainer className="w-full">
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
        </ScrollContainer>
      </SidebarContent>

      <SidebarFooter className="mt-auto">
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
