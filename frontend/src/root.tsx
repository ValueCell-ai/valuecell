import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Links, Meta, Outlet, Scripts, ScrollRestoration } from "react-router";
import AppSidebar from "@/components/valuecell/app-sidebar";
import { Toaster } from "./components/ui/sonner";

import "overlayscrollbars/overlayscrollbars.css";
import "./global.css";
import { SidebarProvider } from "./components/ui/sidebar";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
        <link rel="icon" type="image/svg+xml" href="/logo.svg" />
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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // Global default 5 minutes fresh time
      gcTime: 30 * 60 * 1000, // Global default 30 minutes garbage collection time
      refetchOnWindowFocus: false, // Don't refetch on window focus by default
      retry: 2, // Default retry 2 times on failure
    },
    mutations: {
      retry: 1, // Default retry 1 time for mutations
    },
  },
});

import { AutoUpdateCheck } from "@/components/valuecell/auto-update-check";
import { BackendHealthCheck } from "@/components/valuecell/backend-health-check";

export default function Root() {
  return (
    <QueryClientProvider client={queryClient}>
      <BackendHealthCheck>
        <SidebarProvider>
          <div className="fixed flex size-full overflow-hidden">
            <AppSidebar />

            <main
              className="relative flex flex-1 overflow-hidden"
              id="main-content"
            >
              <Outlet />
            </main>
            <Toaster />
          </div>
        </SidebarProvider>
        <AutoUpdateCheck />
      </BackendHealthCheck>
    </QueryClientProvider>
  );
}
