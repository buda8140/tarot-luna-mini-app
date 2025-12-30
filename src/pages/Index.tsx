import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, ExternalLink } from 'lucide-react';
import { PageTransition } from '@/components/PageTransition';
import { BalanceDisplay } from '@/components/BalanceDisplay';
import { MenuCard } from '@/components/MenuCard';
import { Button } from '@/components/ui/button';
import { getUser, getTelegramWebApp } from '@/lib/telegram';
import { READING_TYPES, ReadingType } from '@/lib/tarot-data';
import { useUser } from '@/contexts/UserContext';

// Check if running inside Telegram
const checkIsInTelegram = (): boolean => {
  const webApp = getTelegramWebApp();
  return !!(webApp && webApp.initData && webApp.initData.length > 0);
};

const Index = () => {
  const navigate = useNavigate();
  const telegramUser = getUser();
  const { user, isLoading, error, isApiConnected, apiUrl } = useUser();

  const handleReadingSelect = (type: ReadingType) => {
    navigate(`/reading?type=${type}`);
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  // Состояние загрузки
  if (isLoading) {
    return (
      <PageTransition>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className="inline-block mb-4"
            >
              <Sparkles className="w-10 h-10 text-mystic-gold" />
            </motion.div>
            <p className="text-muted-foreground">Подключение к серверу...</p>
          </div>
        </div>
      </PageTransition>
    );
  }

  // Не в Telegram
  if (!checkIsInTelegram()) {
    return (
      <PageTransition>
        <div className="flex items-center justify-center min-h-[60vh] px-4">
          <div className="text-center mystic-card p-8 max-w-md w-full">
            <div className="text-6xl mb-4">🔮</div>
            <h2 className="text-2xl font-serif font-bold mb-4">
              Tarot Luna
            </h2>
            <p className="text-muted-foreground mb-6">
              Это приложение работает только внутри Telegram.
            </p>
            <p className="text-sm text-muted-foreground">
              Откройте бота <span className="text-mystic-gold">@TarotLunaSunBot</span> в Telegram и нажмите кнопку "Открыть"
            </p>
          </div>
        </div>
      </PageTransition>
    );
  }

  // Ошибка подключения к API
  if (error || !isApiConnected || !user) {
    return (
      <PageTransition>
        <div className="flex items-center justify-center min-h-[60vh] px-4">
          <div className="text-center mystic-card p-8 max-w-md w-full">
            <div className="text-4xl mb-4">⚠️</div>
            <h2 className="text-xl font-serif font-bold mb-2">
              Ошибка подключения
            </h2>
            <p className="text-muted-foreground mb-4">
              {error || 'Сервер недоступен'}
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              API: {apiUrl}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.reload()}
            >
              Повторить
            </Button>
          </div>
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="px-4 pt-6 pb-24">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-6"
        >
          <div>
            <h1 className="text-2xl font-serif font-bold">
              Привет, <span className="gold-text">{telegramUser.first_name}</span>
            </h1>
            <p className="text-sm text-muted-foreground">
              Уровень {user?.level || 1} • {user?.total_readings || 0} раскладов
            </p>
          </div>
          <BalanceDisplay />
        </motion.div>

        {/* Hero Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="relative overflow-hidden rounded-2xl p-6 mb-6"
          style={{
            background: 'linear-gradient(135deg, hsl(270 60% 20%) 0%, hsl(280 50% 15%) 100%)',
          }}
        >
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-5 h-5 text-mystic-gold" />
              <span className="text-sm font-medium text-mystic-gold">Карта дня</span>
            </div>
            <h2 className="text-xl font-serif font-bold mb-2">
              Узнай, что приготовила судьба
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Получи персональный расклад от твоей подруги-таролога Луны
            </p>
            <Button
              variant="mystic"
              size="lg"
              onClick={() => handleReadingSelect('random')}
              className="w-full sm:w-auto"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              Получить расклад
            </Button>
          </div>
          <div className="absolute -right-8 -top-8 w-32 h-32 rounded-full bg-mystic-violet/20 blur-2xl" />
          <div className="absolute -left-4 -bottom-4 w-24 h-24 rounded-full bg-primary/20 blur-xl" />
        </motion.div>

        {/* Balance info */}
        {(user?.requests_left === 0 && user?.premium_requests === 0) && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mystic-card p-4 mb-6 border-mystic-gold/30"
          >
            <p className="text-sm text-center">
              У тебя закончились запросы 😢
              <br />
              <button 
                onClick={() => navigate('/shop')} 
                className="text-mystic-gold hover:underline font-medium"
              >
                Купить премиум запросы →
              </button>
            </p>
          </motion.div>
        )}

        {/* Reading Types */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="mb-6"
        >
          <motion.h2
            variants={itemVariants}
            className="text-lg font-serif font-semibold mb-3"
          >
            Виды раскладов
          </motion.h2>
          <div className="grid grid-cols-1 gap-3">
            {(Object.entries(READING_TYPES) as [ReadingType, typeof READING_TYPES[ReadingType]][]).map(
              ([key, { name, description, icon }]) => (
                <motion.div key={key} variants={itemVariants}>
                  <MenuCard
                    icon={icon}
                    title={name}
                    description={description}
                    onClick={() => handleReadingSelect(key)}
                    isPremium={key === 'custom'}
                  />
                </motion.div>
              )
            )}
          </div>
        </motion.div>

        {/* Quick Links */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-2 gap-3 mb-6"
        >
          <motion.div variants={itemVariants}>
            <MenuCard
              icon="🏆"
              title="Достижения"
              onClick={() => navigate('/achievements')}
            />
          </motion.div>
          <motion.div variants={itemVariants}>
            <MenuCard
              icon="👥"
              title="Рефералы"
              description={user?.referrals_count ? `${user.referrals_count} друзей` : undefined}
              onClick={() => navigate('/profile?tab=referrals')}
            />
          </motion.div>
          <motion.div variants={itemVariants}>
            <MenuCard
              icon="📜"
              title="История"
              onClick={() => navigate('/history')}
            />
          </motion.div>
          <motion.div variants={itemVariants}>
            <MenuCard
              icon="💎"
              title="Магазин"
              onClick={() => navigate('/shop')}
            />
          </motion.div>
        </motion.div>

        {/* Support */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center text-sm text-muted-foreground"
        >
          <button
            onClick={() => window.open('https://t.me/TarotLunaSunBot', '_blank')}
            className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
          >
            Нужна помощь?
            <ExternalLink className="w-3 h-3" />
          </button>
        </motion.div>
      </div>
    </PageTransition>
  );
};

export default Index;
