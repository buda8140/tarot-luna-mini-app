// Telegram WebApp SDK integration
declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
}

interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

interface MainButton {
  text: string;
  color: string;
  textColor: string;
  isVisible: boolean;
  isActive: boolean;
  isProgressVisible: boolean;
  setText: (text: string) => MainButton;
  onClick: (callback: () => void) => MainButton;
  offClick: (callback: () => void) => MainButton;
  show: () => MainButton;
  hide: () => MainButton;
  enable: () => MainButton;
  disable: () => MainButton;
  showProgress: (leaveActive?: boolean) => MainButton;
  hideProgress: () => MainButton;
  setParams: (params: { text?: string; color?: string; text_color?: string; is_active?: boolean; is_visible?: boolean }) => MainButton;
}

interface HapticFeedback {
  impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
  notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
  selectionChanged: () => void;
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: {
    query_id?: string;
    user?: TelegramUser;
    auth_date?: number;
    hash?: string;
    start_param?: string;
  };
  version: string;
  platform: string;
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  headerColor: string;
  backgroundColor: string;
  MainButton: MainButton;
  HapticFeedback: HapticFeedback;
  ready: () => void;
  expand: () => void;
  close: () => void;
  sendData: (data: string) => void;
  openLink: (url: string, options?: { try_instant_view?: boolean }) => void;
  openTelegramLink: (url: string) => void;
  setHeaderColor: (color: string) => void;
  setBackgroundColor: (color: string) => void;
  enableClosingConfirmation: () => void;
  disableClosingConfirmation: () => void;
  showPopup: (params: { title?: string; message: string; buttons?: Array<{ id?: string; type?: string; text?: string }> }, callback?: (id: string) => void) => void;
  showAlert: (message: string, callback?: () => void) => void;
  showConfirm: (message: string, callback?: (confirmed: boolean) => void) => void;
}

// Get Telegram WebApp instance
export function getTelegramWebApp(): TelegramWebApp | null {
  if (typeof window !== 'undefined' && window.Telegram?.WebApp) {
    return window.Telegram.WebApp;
  }
  return null;
}

// Get current user from Telegram
export function getTelegramUser(): TelegramUser | null {
  const webApp = getTelegramWebApp();
  return webApp?.initDataUnsafe?.user || null;
}

// Check if running inside Telegram with valid initData
export function isInTelegram(): boolean {
  const webApp = getTelegramWebApp();
  return !!(webApp && webApp.initData && webApp.initData.length > 0);
}

// Initialize Telegram WebApp
export function initTelegramApp(): void {
  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.ready();
    webApp.expand();
    webApp.setHeaderColor('#0f001a');
    webApp.setBackgroundColor('#0f001a');
  }
}

// Haptic feedback helpers
export const haptic = {
  light: () => getTelegramWebApp()?.HapticFeedback?.impactOccurred('light'),
  medium: () => getTelegramWebApp()?.HapticFeedback?.impactOccurred('medium'),
  heavy: () => getTelegramWebApp()?.HapticFeedback?.impactOccurred('heavy'),
  success: () => getTelegramWebApp()?.HapticFeedback?.notificationOccurred('success'),
  error: () => getTelegramWebApp()?.HapticFeedback?.notificationOccurred('error'),
  warning: () => getTelegramWebApp()?.HapticFeedback?.notificationOccurred('warning'),
  selection: () => getTelegramWebApp()?.HapticFeedback?.selectionChanged(),
};

// Open external link
export function openLink(url: string): void {
  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.openLink(url);
  } else {
    window.open(url, '_blank');
  }
}

// Main button helpers
export const mainButton = {
  show: (text: string, onClick: () => void) => {
    const webApp = getTelegramWebApp();
    if (webApp) {
      webApp.MainButton.setText(text).onClick(onClick).show();
    }
  },
  hide: () => {
    const webApp = getTelegramWebApp();
    if (webApp) {
      webApp.MainButton.hide();
    }
  },
  showProgress: () => {
    const webApp = getTelegramWebApp();
    if (webApp) {
      webApp.MainButton.showProgress();
    }
  },
  hideProgress: () => {
    const webApp = getTelegramWebApp();
    if (webApp) {
      webApp.MainButton.hideProgress();
    }
  },
};

// Mock user for development outside Telegram
export function getMockUser(): TelegramUser {
  return {
    id: 123456789,
    first_name: 'Luna',
    last_name: 'Tarot',
    username: 'lunatarot',
    language_code: 'ru',
    is_premium: true,
  };
}

// Get user (real or mock for development)
export function getUser(): TelegramUser {
  return getTelegramUser() || getMockUser();
}

export type { TelegramWebApp, TelegramUser, ThemeParams, MainButton, HapticFeedback };
