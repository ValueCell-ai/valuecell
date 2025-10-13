import {
  index,
  layout,
  prefix,
  type RouteConfig,
  route,
} from "@react-router/dev/routes";

export default [
  index("app/redirect-to-home.tsx"),
  ...prefix("/home", [
    layout("app/home/_layout.tsx", [
      index("app/home/home.tsx"),
      route("/stock/:stockId", "app/home/stock.tsx"),
    ]),
  ]),
  ...prefix("/agent", [
    route("/:agentName", "app/agent/chat.tsx"),
    route("/:agentName/config", "app/agent/config.tsx"),
  ]),
] satisfies RouteConfig;
