import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode, useRef } from 'react';
import { authUser, getApiUser, UserData, UserStats, checkApiHealth, getApiUrl } from '@/lib/api';
import { getUser as getTelegramUser, getTelegramWebApp } from '@/lib/telegram';
import { toast } from '@/hooks/use-toast';

// Check if running inside Telegram
const checkIsInTelegram = (): boolean => {
  const webApp = getTelegramWebApp();
  return !!(webApp && webApp.initData && webApp.initData.length > 0);
};

interface UserContextType {
  user: UserData | null;
  stats: UserStats | null;
  isLoading: boolean;
  error: string | null;
  isApiConnected: boolean;
  apiUrl: string;
  agreedRules: boolean;
  refreshUser: () => Promise<void>;
  setAgreedRules: (agreed: boolean) => void;
  spendRequest: (isPremium: boolean) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within UserProvider');
  }
  return context;
};

interface UserProviderProps {
  children: ReactNode;
}

export const UserProvider: React.FC<UserProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserData | null>(null);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isApiConnected, setIsApiConnected] = useState(false);
  const apiUrl = getApiUrl();
  const [agreedRules, setAgreedRulesState] = useState(() => {
    return localStorage.getItem('tarot_agreed_rules') === 'true';
  });
  
  // Ref для отслеживания предыдущего баланса (для toast уведомлений)
  const prevPremiumRequestsRef = useRef<number | null>(null);

  // Загрузка данных пользователя
  const refreshUser = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Проверяем, что мы в Telegram
      if (!checkIsInTelegram()) {
        setError('Приложение должно быть открыто в Telegram');
        setIsLoading(false);
        return;
      }

      // Проверяем доступность API
      const healthResult = await checkApiHealth();
      setIsApiConnected(healthResult.ok);
      
      if (!healthResult.ok) {
        setError(`Сервер недоступен: ${healthResult.error}`);
        setIsLoading(false);
        return;
      }

      // Авторизуемся
      const authResult = await authUser();
      
      if (authResult.error) {
        setError(authResult.error);
        setIsLoading(false);
        return;
      }

      // Получаем данные пользователя
      const result = await getApiUser();
      
      if (result.error) {
        setError(result.error);
      } else if (result.user) {
        // Проверяем, увеличился ли баланс premium_requests (платёж зачислен)
        if (prevPremiumRequestsRef.current !== null && 
            result.user.premium_requests > prevPremiumRequestsRef.current) {
          const added = result.user.premium_requests - prevPremiumRequestsRef.current;
          console.log(`[UserContext] 🎉 Payment confirmed! +${added} premium requests`);
          
          // Показываем красивое уведомление
          toast({
            title: "🎉 Оплата прошла успешно!",
            description: `Начислено +${added} ${added === 1 ? 'запрос' : added < 5 ? 'запроса' : 'запросов'}`,
          });
        }
        
        // Обновляем ref для следующего сравнения
        prevPremiumRequestsRef.current = result.user.premium_requests;
        
        setUser(result.user);
        setStats(result.stats);
        
        // Синхронизация согласия с правилами
        if (result.user.agreed_rules) {
          setAgreedRulesState(true);
          localStorage.setItem('tarot_agreed_rules', 'true');
        }
      }
    } catch (err) {
      console.error('Error loading user:', err);
      setError('Ошибка подключения к серверу');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Первичная загрузка
  useEffect(() => {
    refreshUser();
  }, []);

  // Polling для обновления баланса (для проверки платежей)
  useEffect(() => {
    // Проверяем, вернулся ли пользователь из оплаты
    const urlParams = new URLSearchParams(window.location.search);
    const fromPayment = urlParams.get('from_payment') === 'true';
    
    if (fromPayment) {
      // Убираем параметр из URL
      const newUrl = window.location.pathname;
      window.history.replaceState({}, '', newUrl);
      
      // Запускаем частое обновление баланса в течение 2 минут
      let pollCount = 0;
      const maxPolls = 24; // 24 * 5 секунд = 2 минуты
      
      const pollInterval = setInterval(async () => {
        pollCount++;
        console.log(`[Payment Poll] Check ${pollCount}/${maxPolls}`);
        
        await refreshUser();
        
        if (pollCount >= maxPolls) {
          clearInterval(pollInterval);
          console.log('[Payment Poll] Finished polling');
        }
      }, 5000);
      
      return () => clearInterval(pollInterval);
    }
  }, [refreshUser]);

  // Сохранение согласия с правилами
  const setAgreedRules = useCallback((agreed: boolean) => {
    setAgreedRulesState(agreed);
    localStorage.setItem('tarot_agreed_rules', agreed ? 'true' : 'false');
    
    if (user) {
      setUser({ ...user, agreed_rules: agreed });
    }
  }, [user]);

  // Локальное обновление баланса после расклада
  const spendRequest = useCallback((isPremium: boolean) => {
    if (!user) return;
    
    if (isPremium) {
      setUser({
        ...user,
        premium_requests: Math.max(0, user.premium_requests - 1),
        total_readings: user.total_readings + 1,
      });
    } else {
      setUser({
        ...user,
        requests_left: Math.max(0, user.requests_left - 1),
        total_readings: user.total_readings + 1,
      });
    }
    
    if (stats) {
      setStats({
        ...stats,
        total_readings: stats.total_readings + 1,
      });
    }
    
    // Синхронизируем с сервером
    setTimeout(() => {
      refreshUser();
    }, 1000);
  }, [user, stats, refreshUser]);

  return (
    <UserContext.Provider
      value={{
        user,
        stats,
        isLoading,
        error,
        isApiConnected,
        apiUrl,
        agreedRules,
        refreshUser,
        setAgreedRules,
        spendRequest,
      }}
    >
      {children}
    </UserContext.Provider>
  );
};