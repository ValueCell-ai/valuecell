import { Links, Meta, Outlet, Scripts, ScrollRestoration } from "react-router";
import AppSidebar from "@/components/valuecell/app-sidebar";

import "overlayscrollbars/overlayscrollbars.css";
import "./global.css";

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

export default function Root() {
  return (
    <div className="fixed flex size-full overflow-hidden">
      <AppSidebar />

      <Outlet />
    </div>
  );
}
