// frontend/src/App.jsx
// If you don't have react-router-dom yet: npm install react-router-dom

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import SignUp from "./pages/SignUp";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Default route → signup */}
        <Route path="/"       element={<Navigate to="/signup" replace />} />
        <Route path="/signup" element={<SignUp />} />

        {/* Placeholder: add Login, Dashboard etc. here later */}
        {/* <Route path="/login"     element={<Login />} /> */}
        {/* <Route path="/dashboard" element={<Dashboard />} /> */}
      </Routes>
    </BrowserRouter>
  );
}
