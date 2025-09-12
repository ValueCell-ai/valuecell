import { type RouteConfig, route } from "@react-router/dev/routes";
import { flatRoutes } from "@react-router/fs-routes";

export default [
  route("/", "app/_home/route.tsx"),
  ...(await flatRoutes({
    rootDirectory: "app",
  })),
] satisfies RouteConfig;
