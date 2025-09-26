import {
  type FC,
  type HTMLAttributes,
  memo,
  type ReactNode,
  useMemo,
} from "react";
import { NavLink, useLocation } from "react-router";
import { useGetAgentList } from "@/api/agent";
import { BookOpen, ChartBarVertical, Logo, Setting, User } from "@/assets/svg";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
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
        "flex w-20 flex-col items-center gap-3 bg-neutral-100 px-4 py-5",
        className,
      )}
    >
      {children}
    </div>
  );
};

const SidebarHeader: FC<SidebarHeaderProps> = ({ children, className }) => {
  return <div className={className}>{children}</div>;
};

const SidebarContent: FC<SidebarContentProps> = ({ children, className }) => {
  return (
    <div className={cn("flex flex-1 flex-col gap-3", className)}>
      {children}
    </div>
  );
};

const SidebarFooter: FC<SidebarFooterProps> = ({ children, className }) => {
  return <div className={cn("flex flex-col gap-3", className)}>{children}</div>;
};

const SidebarMenu: FC<SidebarMenuProps> = ({ children, className }) => {
  return <div className={cn("flex flex-col gap-3", className)}>{children}</div>;
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
        "box-border flex size-12 items-center justify-center rounded-full",
        "cursor-pointer transition-all",
        type === "button" && [
          "bg-neutral-200 p-3",
          "hover:data-[active=false]:bg-neutral-300",
          "data-[active=true]:bg-black data-[active=true]:text-white",
        ],
        type === "agent" && [
          "border border-neutral-200 bg-white",
          "hover:data-[active=false]:border-neutral-300",
          "data-[active=true]:border-black",
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
  const { pathname } = useLocation();
  const prefixPath = pathname.split("/")[1];

  const navItems = useMemo(() => {
    return {
      home: [
        {
          id: "home",
          icon: Logo,
          label: "Home",
          to: "/",
        },
      ],
      config: [
        {
          id: "chart",
          icon: ChartBarVertical,
          label: "Chart",
          to: "chart",
        },
        { id: "book", icon: BookOpen, label: "Book", to: "book" },
        {
          id: "settings",
          icon: Setting,
          label: "Settings",
          to: "settings",
        },
        { id: "user", icon: User, label: "User", to: "user" },
      ],
    };
  }, []);

  const { data: agentList } = useGetAgentList({ enabled_only: true });
  const agentItems = useMemo(() => {
    return agentList?.map((agent) => ({
      id: agent.agent_name,
      icon: agent.icon_url,
      label: agent.agent_name,
      to: `/agent/${agent.agent_name}`,
    }));
  }, [agentList]);

  // verify the button is active
  const verifyActive = (to: string) => `/${prefixPath}` === to;

  return (
    <Sidebar>
      <SidebarHeader>
        <NavLink to={navItems.home[0].to}>
          <SidebarMenuItem
            aria-label={navItems.home[0].label}
            data-active={verifyActive(navItems.home[0].to)}
            className="p-2"
          >
            <SvgIcon name={Logo} />
          </SidebarMenuItem>
        </NavLink>
      </SidebarHeader>

      <Separator />

      <SidebarContent className="max-h-[calc(100vh-11rem)]">
        <ScrollContainer>
          <SidebarMenu>
            {agentItems?.map((item) => {
              return (
                <NavLink key={item.id} to={item.to}>
                  <SidebarMenuItem
                    type="agent"
                    aria-label={item.label}
                    data-active={verifyActive(item.to)}
                  >
                    <Avatar className="size-full">
                      <AvatarImage src={item.icon} />
                      <AvatarFallback>{item.label.slice(0, 2)}</AvatarFallback>
                    </Avatar>
                  </SidebarMenuItem>
                </NavLink>
              );
            })}
          </SidebarMenu>
        </ScrollContainer>
      </SidebarContent>

      {/* <SidebarFooter className="mt-auto">
        <SidebarMenu>
          {navItems.config.map((item) => {
            return (
              <NavLink key={item.id} to={item.to}>
                <SidebarMenuItem
                  aria-label={item.label}
                  data-active={verifyActive(item.to)}
                >
                  <SvgIcon name={item.icon} />
                </SidebarMenuItem>
              </NavLink>
            );
          })}
        </SidebarMenu>
      </SidebarFooter> */}
    </Sidebar>
  );
};

export default memo(AppSidebar);
