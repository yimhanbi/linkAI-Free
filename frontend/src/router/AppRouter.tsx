import { Navigate, Route, Routes } from "react-router-dom";
import { useState, useEffect } from "react";
import MainLayout from "../View/layout/MainLayout";
import AdvancedSearchPage from "../View/advancedSearch/AdvancedSearchPage";
import LoginPage from "@/View/auth/LoginPage";
import WelcomePage from "../View/home/WelcomePage";

export default function AppRouter() {
  // 1. 로컬 스토리지에서 토큰 확인 (로그인 여부) - 상태로 관리하여 변경 감지
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem("token"));

  // 2. localStorage 변경 감지
  useEffect(() => {
    const checkAuth = () => {
      setIsLoggedIn(!!localStorage.getItem("token"));
    };

    // 초기 확인
    checkAuth();

    // storage 이벤트 리스너 (다른 탭에서의 변경 감지)
    window.addEventListener("storage", checkAuth);

    // 커스텀 이벤트 리스너 (같은 탭에서의 변경 감지)
    window.addEventListener("authChange", checkAuth);

    return () => {
      window.removeEventListener("storage", checkAuth);
      window.removeEventListener("authChange", checkAuth);
    };
  }, []);

  return (
    <Routes>
      {/* 홈(/) = 웰컴 화면만 (사이드바·상단바 없음) */}
      <Route
        path="/"
        element={isLoggedIn ? <WelcomePage /> : <Navigate to="/login" replace />}
      />

      {/* /welcome 접근 시 홈으로 리다이렉트 */}
      <Route path="/welcome" element={<Navigate to="/" replace />} />

      {/* 로그인 페이지: 레이아웃 없이 단독 */}
      <Route
        path="/login"
        element={isLoggedIn ? <Navigate to="/" replace /> : <LoginPage />}
      />

      {/* 사이드바·상단바 있는 서비스 영역 (advanced-search, chatbot) */}
      <Route element={isLoggedIn ? <MainLayout /> : <Navigate to="/login" replace />}>
        <Route path="/advanced-search" element={<AdvancedSearchPage />} />
        <Route path="/chatbot" element={<div />} />
      </Route>

      <Route path="*" element={<h1>Not Found</h1>} />
    </Routes>
  );
}