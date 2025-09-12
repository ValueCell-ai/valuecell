import { Links, Meta, Outlet, Scripts, ScrollRestoration } from "react-router";
import AppSidebar from "@/components/app_sidebar";
import { SidebarProvider } from "@/components/ui/sidebar";

import "./global.css";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
        <link rel="icon" type="image/svg+xml" href="/vite.svg" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Value Cell</title>
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function Root() {
  return (
    <SidebarProvider
      open={false}
      className="fixed flex h-full w-full overflow-hidden"
    >
      <AppSidebar />

      <main className="flex-1 overflow-hidden rounded-tl-3xl">
        <Outlet />
      </main>
    </SidebarProvider>
  );
}
