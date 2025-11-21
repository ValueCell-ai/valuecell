import { Brain, Cpu, Settings } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router";
import {
  Item,
  ItemContent,
  ItemGroup,
  ItemMedia,
  ItemTitle,
} from "@/components/ui/item";
import { cn } from "@/lib/utils";

const settingNavItems = [
  {
    id: "models",
    icon: Cpu,
    label: "Models",
    path: "/setting",
  },
  {
    id: "general",
    icon: Settings,
    label: "General",
    path: "/setting/general",
  },
  {
    id: "memory",
    icon: Brain,
    label: "Memory",
    path: "/setting/memory",
  },
  // {
  //   id: "language",
  //   icon: Globe,
  //   label: "Language",
  //   path: "/setting/language",
  // },
  // {
  //   id: "about",
  //   icon: Info,
  //   label: "About us",
  //   path: "/setting/about",
  // },
];

export default function SettingLayout() {
  const location = useLocation();

  return (
    <div className="flex size-full overflow-hidden bg-gray-100">
      {/* Left navigation */}
      <aside className="flex w-52 flex-col gap-4 rounded-tl-xl rounded-bl-xl bg-white px-6 py-8">
        <div className="flex flex-col gap-4">
          <h2 className="font-bold text-gray-950 text-xl">Settings</h2>

          <ItemGroup className="gap-1">
            {settingNavItems.map((navItem) => {
              const isActive = location.pathname === navItem.path;
              const Icon = navItem.icon;

              return (
                <Item
                  key={navItem.id}
                  variant={isActive ? "muted" : "default"}
                  size="sm"
                  className={cn(
                    "cursor-pointer px-3 py-2.5",
                    isActive ? "bg-gray-100" : "bg-white hover:bg-gray-50",
                  )}
                  asChild
                >
                  <NavLink to={navItem.path}>
                    <ItemMedia>
                      <Icon className="size-5" />
                    </ItemMedia>
                    <ItemContent>
                      <ItemTitle>{navItem.label}</ItemTitle>
                    </ItemContent>
                  </NavLink>
                </Item>
              );
            })}
          </ItemGroup>
        </div>
      </aside>

      {/* Right content area */}
      <main className="flex flex-1 overflow-hidden rounded-tr-xl rounded-br-xl bg-white">
        <Outlet />
      </main>
    </div>
  );
}
