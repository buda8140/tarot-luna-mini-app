// API клиент для связи с бэкендом Tarot Luna
import { getTelegramWebApp, getUser } from './telegram';

// API URL из переменных окружения (обязательно для production)
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Типы данных
export interface UserData {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  requests_left: number;
  premium_requests: number;
  referrals_count: number;
  is_banned: boolean;
  agreed_rules: boolean;
  level: number;
  total_readings: number;
}

export interface UserStats {
  total_readings: number;
  avg_cards: number;
  favorite_type?: string;
  active_days: number;
}

export interface ReadingCard {
  id: number;
  name: string;
  nameRu: string;
  image: string;
  isReversed?: boolean;
  meaning?: string;
  meaningReversed?: string;
}

export interface ReadingResult {
  cards: ReadingCard[];
  interpretation: string;
  reading_type: string;
  is_premium: boolean;
}

export interface PaymentPackage {
  package_key: string;
  name: string;
  requests: number;
  price: number;
  popular?: boolean;
  discount?: string;
}

export interface HistoryItem {
  id: number;
  question: string;
  cards: string;
  response: string;
  reading_type: string;
  is_premium: boolean;
  timestamp?: string;  // From SQLite DB
  created_at?: string; // Alternative field name
}

// Получить initData для авторизации Telegram
function getInitData(): string {
  const webApp = getTelegramWebApp();
  return webApp?.initData || '';
}

// API запрос с обработкой ошибок
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ success: boolean; data?: T; error?: string }> {
  if (!API_BASE_URL) {
    return { success: false, error: 'API URL не настроен (VITE_API_URL)' };
  }

  try {
    const initData = getInitData();
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData,
        ...options.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return { success: false, error: data.error || `HTTP ${response.status}` };
    }

    return { success: true, data };
  } catch (error) {
    console.error(`[API Error] ${endpoint}:`, error);
    return { success: false, error: 'Ошибка подключения к серверу' };
  }
}

// ==================== API МЕТОДЫ ====================

// Авторизация через Telegram initData
export async function authUser(): Promise<{ user: UserData | null; error?: string }> {
  const initData = getInitData();
  const telegramUser = getUser();
  
  const result = await apiRequest<{ user: UserData; token?: string }>('/api/auth', {
    method: 'POST',
    body: JSON.stringify({ 
      initData,
      user_id: telegramUser.id,
      username: telegramUser.username,
      first_name: telegramUser.first_name,
      last_name: telegramUser.last_name,
    }),
  });

  if (!result.success) {
    return { user: null, error: result.error };
  }

  return { user: result.data?.user || null };
}

// Получить данные пользователя из БД
export async function getApiUser(): Promise<{
  user: UserData | null;
  stats: UserStats | null;
  error?: string;
}> {
  const telegramUser = getUser();
  
  const result = await apiRequest<{ user: UserData; stats: UserStats }>(
    `/api/user?user_id=${telegramUser.id}`
  );
  
  if (!result.success) {
    return { user: null, stats: null, error: result.error };
  }
  
  return {
    user: result.data?.user || null,
    stats: result.data?.stats || null,
  };
}

// Создать расклад через реальный API
export async function createReading(
  question: string,
  cardsCount: number,
  readingType: string,
  usePremium: boolean,
  cards?: { nameRu: string; isReversed?: boolean }[]
): Promise<{ success: boolean; reading?: ReadingResult; error?: string }> {
  const telegramUser = getUser();
  
  // Формируем список карт для отправки на сервер
  const cardNames = cards?.map(card => {
    const name = card.nameRu;
    return card.isReversed ? `${name} (перевернутая)` : name;
  }) || [];
  
  const result = await apiRequest<{ reading: ReadingResult }>('/api/reading', {
    method: 'POST',
    body: JSON.stringify({
      user_id: telegramUser.id,
      question,
      cards_count: cardsCount,
      reading_type: readingType,
      use_premium: usePremium,
      cards: cardNames, // Передаем выбранные карты
    }),
  });

  if (!result.success) {
    return { success: false, error: result.error };
  }

  return { success: true, reading: result.data?.reading };
}

// Создание платежа через API (записывает pending в БД)
export async function createPayment(
  packageKey: string
): Promise<{
  success: boolean;
  payment?: {
    url: string;
    label: string;
    amount: number;
    requests: number;
    package_key: string;
  };
  error?: string;
}> {
  const telegramUser = getUser();
  
  console.log('[API] createPayment called:', { packageKey, userId: telegramUser.id });
  
  const result = await apiRequest<{
    payment: {
      url: string;
      label: string;
      amount: number;
      requests: number;
      package_key: string;
    };
  }>('/api/payment', {
    method: 'POST',
    body: JSON.stringify({
      user_id: telegramUser.id,
      package_key: packageKey,
    }),
  });

  console.log('[API] createPayment result:', result);

  if (!result.success) {
    console.error('[API] createPayment error:', result.error);
    return { success: false, error: result.error };
  }

  console.log('[API] createPayment success, payment:', result.data?.payment);
  return { success: true, payment: result.data?.payment };
}

// Генерация ссылки на оплату YooMoney (deprecated - используй createPayment)
export function generatePaymentLink(
  userId: number,
  packageKey: string,
  price: number
): string {
  const randomKopecks = Math.floor(Math.random() * 99) / 100;
  const finalPrice = (price + randomKopecks).toFixed(2);

  const timestamp = Date.now();
  const randomSuffix = Math.floor(Math.random() * 10000);
  const label = `tarot_luna_user_${userId}_pkg_${packageKey}_${timestamp}_${randomSuffix}`;

  const params = new URLSearchParams({
    writer: 'seller',
    targets: 'Tarot',
    'default-sum': finalPrice,
    'button-text': '11',
    'payment-type-choice': 'on',
    'mobile-payment-type-choice': 'on',
    comment: 'off',
    hint: '',
    successURL: '',
    quickpay: 'shop',
    account: '4100119427014137',
    label: label,
  });

  return `https://yoomoney.ru/quickpay/shop-widget?${params.toString()}`;
}

// Получить тарифы из БД
export async function getRates(): Promise<PaymentPackage[]> {
  const result = await apiRequest<{ rates: PaymentPackage[] }>('/api/rates');
  
  if (!result.success || !result.data?.rates) {
    return [
      { package_key: 'buy_1', name: 'Начальный', requests: 5, price: 100 },
      { package_key: 'buy_2', name: 'Популярный', requests: 15, price: 250, popular: true },
      { package_key: 'buy_3', name: 'Максимальный', requests: 35, price: 500 },
    ];
  }
  
  return result.data.rates;
}

// Интерфейс для платежей
export interface PaymentItem {
  id: number;
  amount: number;
  requests: number;
  status: string;
  timestamp: string;
  yoomoney_label?: string;
  tariff_name?: string;
}

// Получить историю раскладов и платежей из БД
export async function getHistory(
  page: number = 0,
  limit: number = 10
): Promise<{ history: HistoryItem[]; payments: PaymentItem[]; total: number; error?: string }> {
  const telegramUser = getUser();
  
  console.log('[API] getHistory called for user:', telegramUser.id);
  
  const result = await apiRequest<{
    history: HistoryItem[];
    payments: PaymentItem[];
    pagination: { total: number };
  }>(`/api/history?user_id=${telegramUser.id}&page=${page}&limit=${limit}`);

  console.log('[API] getHistory result:', result);

  if (!result.success) {
    console.error('[API] getHistory error:', result.error);
    return { history: [], payments: [], total: 0, error: result.error };
  }

  return {
    history: result.data?.history || [],
    payments: result.data?.payments || [],
    total: result.data?.pagination?.total || 0,
  };
}

// Получить достижения из БД
export async function getAchievements(): Promise<{
  achievements: any[];
  level: { level: number; experience: number };
  error?: string;
}> {
  const telegramUser = getUser();
  
  const result = await apiRequest<{
    achievements: any[];
    level: { level: number; experience: number };
  }>(`/api/achievements?user_id=${telegramUser.id}`);

  if (!result.success) {
    return { 
      achievements: [], 
      level: { level: 1, experience: 0 },
      error: result.error 
    };
  }

  return {
    achievements: result.data?.achievements || [],
    level: result.data?.level || { level: 1, experience: 0 },
  };
}

// Забрать бонус за достижение
export async function claimAchievement(achievementKey: string): Promise<{ success: boolean; error?: string }> {
  const telegramUser = getUser();
  
  const result = await apiRequest<{ success: boolean }>('/api/achievements/claim', {
    method: 'POST',
    body: JSON.stringify({
      user_id: telegramUser.id,
      achievement_key: achievementKey,
    }),
  });

  return { success: result.success, error: result.error };
}

// ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

// Форматирование текста
export function cleanInterpretation(text: string): string {
  return text
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/<[^>]*>/g, '')
    .trim();
}

// Разбиение длинного текста на части
export function paginateText(text: string, maxLength: number = 1500): string[] {
  if (text.length <= maxLength) {
    return [text];
  }

  const parts: string[] = [];
  const paragraphs = text.split('\n\n');
  let currentPart = '';

  for (const paragraph of paragraphs) {
    if ((currentPart + '\n\n' + paragraph).length > maxLength) {
      if (currentPart) {
        parts.push(currentPart.trim());
      }
      currentPart = paragraph;
    } else {
      currentPart = currentPart ? currentPart + '\n\n' + paragraph : paragraph;
    }
  }

  if (currentPart) {
    parts.push(currentPart.trim());
  }

  return parts;
}

// Проверка доступности API
export async function checkApiHealth(): Promise<{ ok: boolean; error?: string }> {
  if (!API_BASE_URL) {
    return { ok: false, error: 'VITE_API_URL не настроен' };
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (response.ok) {
      return { ok: true };
    }
    
    return { ok: false, error: `HTTP ${response.status}` };
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Unknown error';
    return { ok: false, error: errorMessage };
  }
}

// Получить API URL
export function getApiUrl(): string {
  return API_BASE_URL || 'Не настроен';
}