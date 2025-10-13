import { Navigate } from "react-router";

export default function RedirectToHome() {
  return <Navigate to="/home" replace />;
}
