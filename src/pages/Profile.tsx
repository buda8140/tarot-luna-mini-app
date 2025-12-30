import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Crown,
  Sparkles,
  Users,
  BarChart3,
  Trophy,
  Copy,
  Check,
  Share2,
} from 'lucide-react';
import { PageTransition } from '@/components/PageTransition';
import { BalanceDisplay } from '@/components/BalanceDisplay';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { useUser } from '@/contexts/UserContext';
import { getUser, haptic } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

const Profile = () => {
  const navigate = useNavigate();
  const telegramUser = getUser();
  const { user, stats, refreshUser, isLoading, error, isApiConnected } = useUser();
  const [copied, setCopied] = useState(false);

  // Обновляем данные при загрузке страницы
  useEffect(() => {
    refreshUser();
  }, []);

  // Показать ошибку если нет подключения
  if (!isApiConnected && !isLoading) {
    return (
      <PageTransition>
        <div className="flex items-center justify-center min-h-[60vh] px-4">
          <div className="text-center mystic-card p-6">
            <p className="text-muted-foreground">{error || 'Запустите бэкенд'}</p>
          </div>
        </div>
      </PageTransition>
    );
  }

  // Реальные данные из контекста
  const level = user?.level ?? 1;
  const experience = (stats?.total_readings ?? user?.total_readings ?? 0) * 5; // 5 XP за расклад
  const xpForNextLevel = (level + 1) * 100;
  
  const userData = {
    freeRequests: user?.requests_left ?? 3,
    premiumRequests: user?.premium_requests ?? 0,
    totalReadings: stats?.total_readings ?? user?.total_readings ?? 0,
    avgCards: stats?.avg_cards ?? 3.0,
    favoriteType: stats?.favorite_type ?? 'Классический',
    activeDays: stats?.active_days ?? 0,
    level: level,
    xp: experience,
    xpToNext: xpForNextLevel,
    referralCount: user?.referrals_count ?? 0,
    referralLink: `https://t.me/TarotLunaSunBot?start=ref_${user?.id ?? telegramUser.id}`,
  };

  const statsList = [
    { icon: BarChart3, label: 'Раскладов', value: userData.totalReadings },
    { icon: Sparkles, label: 'Ср. карт', value: userData.avgCards.toFixed(1) },
    { icon: Trophy, label: 'Дней активности', value: userData.activeDays },
    { icon: Users, label: 'Рефералов', value: userData.referralCount },
  ];

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(userData.referralLink);
      setCopied(true);
      haptic.success();
      toast.success('Ссылка скопирована!');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      haptic.error();
      toast.error('Не удалось скопировать');
    }
  };

  const handleShare = () => {
    haptic.light();
    if (navigator.share) {
      navigator.share({
        title: 'Таро Luna',
        text: 'Присоединяйся к магии Таро! 🔮 Получи бесплатные расклады!',
        url: userData.referralLink,
      });
    } else {
      handleCopyLink();
    }
  };

  return (
    <PageTransition>
      <div className="px-3 pt-4 pb-20">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 mb-4"
        >
          <button
            onClick={() => navigate(-1)}
            className="p-1.5 rounded-lg hover:bg-muted transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex-1">
            <h1 className="text-lg font-serif font-bold">Мой профиль</h1>
          </div>
          <BalanceDisplay />
        </motion.div>

        {/* User Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mystic-card p-4 mb-4"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center flex-shrink-0">
              <span className="text-lg font-serif font-bold">
                {telegramUser.first_name.charAt(0)}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-base font-bold truncate">
                {telegramUser.first_name} {telegramUser.last_name}
              </h2>
              {telegramUser.username && (
                <p className="text-xs text-muted-foreground truncate">@{telegramUser.username}</p>
              )}
              {telegramUser.is_premium && (
                <span className="inline-flex items-center gap-1 mt-0.5 px-1.5 py-0.5 rounded-full bg-mystic-gold/20 text-mystic-gold text-xs font-medium">
                  <Crown className="w-2.5 h-2.5" />
                  Premium
                </span>
              )}
            </div>
          </div>

          {/* Level Progress */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Уровень {userData.level}</span>
              <span className="text-muted-foreground">
                {userData.xp}/{userData.xpToNext} XP
              </span>
            </div>
            <Progress
              value={(userData.xp / userData.xpToNext) * 100}
              className="h-1.5"
            />
          </div>
        </motion.div>

        {/* Stats Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-4 gap-2 mb-4"
        >
          {statsList.map(({ icon: Icon, label, value }, index) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.15 + index * 0.05 }}
              className="mystic-card p-2 text-center"
            >
              <Icon className="w-3.5 h-3.5 mx-auto mb-0.5 text-primary" />
              <p className="text-base font-bold leading-tight">{value}</p>
              <p className="text-[9px] text-muted-foreground leading-tight">{label}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* Tabs */}
        <Tabs defaultValue="stats" className="w-full">
          <TabsList className="w-full bg-card/60 border border-border/50">
            <TabsTrigger value="stats" className="flex-1">
              Статистика
            </TabsTrigger>
            <TabsTrigger value="referrals" className="flex-1">
              Рефералы
            </TabsTrigger>
          </TabsList>

          <TabsContent value="stats" className="mt-4 space-y-4">
            <div className="mystic-card p-4">
              <h3 className="font-medium mb-3">Любимый тип расклада</h3>
              <p className="text-mystic-gold font-serif">{userData.favoriteType}</p>
            </div>

            <Button
              variant="mystic"
              size="lg"
              className="w-full"
              onClick={() => navigate('/achievements')}
            >
              <Trophy className="w-4 h-4 mr-2" />
              Мои достижения
            </Button>
          </TabsContent>

          <TabsContent value="referrals" className="mt-4 space-y-4">
            <div className="mystic-card p-4">
              <h3 className="font-medium mb-2">Пригласи друзей</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Получи +1 премиум запрос за каждого друга!
              </p>

              <div className="flex gap-2 mb-4">
                <div className="flex-1 p-3 rounded-lg bg-muted/50 text-sm font-mono truncate">
                  {userData.referralLink}
                </div>
                <Button
                  variant="glass"
                  size="icon"
                  onClick={handleCopyLink}
                  className="shrink-0"
                >
                  {copied ? (
                    <Check className="w-4 h-4 text-green-500" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              </div>

              <Button
                variant="gold"
                size="lg"
                className="w-full"
                onClick={handleShare}
              >
                <Share2 className="w-4 h-4 mr-2" />
                Поделиться ссылкой
              </Button>
            </div>

            <div className="mystic-card p-4">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Приглашено друзей</span>
                <span className="text-lg font-bold text-mystic-gold">
                  {userData.referralCount}
                </span>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </PageTransition>
  );
};

export default Profile;