import { type RouteConfig, route } from "@react-router/dev/routes";
import { flatRoutes } from "@react-router/fs-routes";

export default [
  route("/", "app/home/route.tsx"),
  ...(await flatRoutes({
    rootDirectory: "app",
    ignoredRouteFiles: ["app/home"],
  })),
] satisfies RouteConfig;
