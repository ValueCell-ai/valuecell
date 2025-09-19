import {
  index,
  layout,
  prefix,
  type RouteConfig,
  route,
} from "@react-router/dev/routes";

export default [
  layout("app/home/_layout.tsx", [
    index("app/home/home.tsx"),
    route("/stock/:stockId", "app/home/stock.tsx"),
  ]),
  ...prefix("/agent", [
    route("/:agentId", "app/agent/chat.tsx"),
    route("/:agentId/config", "app/agent/config.tsx"),
  ]),
] satisfies RouteConfig;
