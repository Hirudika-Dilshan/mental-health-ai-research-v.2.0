// frontend/src/components/ProtectedRoute.jsx
// Wrap any route with this to require login.
// If not logged in → redirects to /login automatically.

import { Navigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";

export default function ProtectedRoute({ children }) {
  const { isLoggedIn } = useAuth();

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
