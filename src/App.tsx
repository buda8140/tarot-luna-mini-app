import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import { StarryBackground } from "@/components/StarryBackground";
import { Navigation } from "@/components/Navigation";
import { RulesAgreement } from "@/components/RulesAgreement";
import { UserProvider, useUser } from "@/contexts/UserContext";
import { initTelegramApp } from "@/lib/telegram";
import Index from "./pages/Index";
import Reading from "./pages/Reading";
import Profile from "./pages/Profile";
import Shop from "./pages/Shop";
import History from "./pages/History";
import Achievements from "./pages/Achievements";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

// Внутренний компонент для проверки согласия с правилами
const AppContent = () => {
  const { agreedRules, setAgreedRules, isLoading } = useUser();

  // Показываем экран правил если пользователь не согласился
  if (!agreedRules && !isLoading) {
    return (
      <div className="relative min-h-screen">
        <StarryBackground />
        <main className="relative z-10">
          <RulesAgreement onAgree={() => setAgreedRules(true)} />
        </main>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen">
      <StarryBackground />
      <main className="relative z-10">
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/reading" element={<Reading />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/shop" element={<Shop />} />
          <Route path="/history" element={<History />} />
          <Route path="/achievements" element={<Achievements />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Navigation />
    </div>
  );
};

const App = () => {
  useEffect(() => {
    initTelegramApp();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner position="top-center" theme="dark" />
        <BrowserRouter>
          <UserProvider>
            <AppContent />
          </UserProvider>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
