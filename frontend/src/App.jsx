import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import AnxietyTest from "./pages/AnxietyTest";
import Dashboard from "./pages/Dashboard";
import DepressionTest from "./pages/DepressionTest";
import GeneralChat from "./pages/GeneralChat";
import Login from "./pages/Login";
import SignUp from "./pages/SignUp";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={(
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/anxiety-test"
            element={(
              <ProtectedRoute>
                <AnxietyTest />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/depression-test"
            element={(
              <ProtectedRoute>
                <DepressionTest />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/general-chat"
            element={(
              <ProtectedRoute>
                <GeneralChat />
              </ProtectedRoute>
            )}
          />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
