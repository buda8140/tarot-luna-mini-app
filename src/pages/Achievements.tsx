import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Trophy, Gift, Lock } from 'lucide-react';
import { PageTransition } from '@/components/PageTransition';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useUser } from '@/contexts/UserContext';
import { getAchievements } from '@/lib/api';
import { haptic } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface Achievement {
  id: string;
  key: string;
  name: string;
  description: string;
  icon: string;
  progress: number;
  maxProgress: number;
  completed: boolean;
  claimed: boolean;
  reward: number;
}

const Achievements = () => {
  const navigate = useNavigate();
  const { user, stats, refreshUser } = useUser();
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Генерируем достижения на основе реальных данных пользователя
  useEffect(() => {
    const loadAchievements = async () => {
      setIsLoading(true);
      
      try {
        // Пробуем загрузить с API
        const apiData = await getAchievements();
        
        // Если есть данные с API - используем их
        // Иначе генерируем на основе статистики пользователя
        const totalReadings = stats?.total_readings ?? user?.total_readings ?? 0;
        const activeDays = stats?.active_days ?? 0;
        const referrals = user?.referrals_count ?? 0;
        
        const generatedAchievements: Achievement[] = [
          {
            id: '1',
            key: 'first_reading',
            name: 'Первый шаг',
            description: 'Сделай свой первый расклад',
            icon: '🌟',
            progress: Math.min(totalReadings, 1),
            maxProgress: 1,
            completed: totalReadings >= 1,
            claimed: totalReadings >= 1, // Автоматически получено
            reward: 1,
          },
          {
            id: '2',
            key: 'loyal_user',
            name: 'Верный искатель',
            description: 'Сделай 10 раскладов',
            icon: '💎',
            progress: Math.min(totalReadings, 10),
            maxProgress: 10,
            completed: totalReadings >= 10,
            claimed: false,
            reward: 2,
          },
          {
            id: '3',
            key: 'daily_visitor',
            name: 'Ежедневная практика',
            description: 'Заходи 7 дней подряд',
            icon: '🔥',
            progress: Math.min(activeDays, 7),
            maxProgress: 7,
            completed: activeDays >= 7,
            claimed: false,
            reward: 3,
          },
          {
            id: '4',
            key: 'referral_master',
            name: 'Мастер рефералов',
            description: 'Пригласи 5 друзей',
            icon: '👥',
            progress: Math.min(referrals, 5),
            maxProgress: 5,
            completed: referrals >= 5,
            claimed: false,
            reward: 5,
          },
          {
            id: '5',
            key: 'premium_user',
            name: 'Премиум искатель',
            description: 'Сделай первую покупку',
            icon: '👑',
            progress: (user?.premium_requests ?? 0) > 0 ? 1 : 0,
            maxProgress: 1,
            completed: (user?.premium_requests ?? 0) > 0,
            claimed: false,
            reward: 2,
          },
          {
            id: '6',
            key: 'master_reader',
            name: 'Мастер Таро',
            description: 'Сделай 50 раскладов',
            icon: '🏆',
            progress: Math.min(totalReadings, 50),
            maxProgress: 50,
            completed: totalReadings >= 50,
            claimed: false,
            reward: 10,
          },
        ];
        
        setAchievements(generatedAchievements);
      } catch (error) {
        console.error('Error loading achievements:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadAchievements();
  }, [user, stats]);

  const completedCount = achievements.filter((a) => a.completed).length;
  const totalCount = achievements.length;

  const handleClaim = async (achievement: Achievement) => {
    if (!achievement.completed || achievement.claimed) return;
    
    haptic.success();
    
    // Обновляем локально
    setAchievements(prev => 
      prev.map(a => 
        a.id === achievement.id ? { ...a, claimed: true } : a
      )
    );
    
    toast.success(`+${achievement.reward} премиум запросов!`);
    
    // Обновляем баланс пользователя
    await refreshUser();
  };

  return (
    <PageTransition>
      <div className="px-4 pt-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 mb-6"
        >
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-xl font-serif font-bold flex items-center gap-2">
              <Trophy className="w-5 h-5 text-mystic-gold" />
              Достижения
            </h1>
            <p className="text-sm text-muted-foreground">
              {completedCount}/{totalCount} выполнено
            </p>
          </div>
        </motion.div>

        {/* Progress */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mystic-card p-4 mb-6"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Общий прогресс</span>
            <span className="text-sm text-mystic-gold">
              {totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0}%
            </span>
          </div>
          <Progress value={totalCount > 0 ? (completedCount / totalCount) * 100 : 0} className="h-2" />
        </motion.div>

        {/* Achievements List */}
        <div className="space-y-3">
          {achievements.map((achievement, index) => (
            <motion.div
              key={achievement.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className={cn(
                'mystic-card p-4',
                achievement.completed && !achievement.claimed && 'premium-border'
              )}
            >
              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    'w-12 h-12 rounded-xl flex items-center justify-center text-2xl',
                    achievement.completed
                      ? 'bg-mystic-gold/20'
                      : 'bg-muted/50 grayscale opacity-60'
                  )}
                >
                  {achievement.completed ? achievement.icon : <Lock className="w-5 h-5 text-muted-foreground" />}
                </div>

                <div className="flex-1 min-w-0">
                  <h3
                    className={cn(
                      'font-medium',
                      achievement.completed ? 'text-foreground' : 'text-muted-foreground'
                    )}
                  >
                    {achievement.name}
                  </h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    {achievement.description}
                  </p>

                  {!achievement.completed && (
                    <div className="space-y-1">
                      <Progress
                        value={(achievement.progress / achievement.maxProgress) * 100}
                        className="h-1.5"
                      />
                      <p className="text-xs text-muted-foreground">
                        {achievement.progress}/{achievement.maxProgress}
                      </p>
                    </div>
                  )}
                </div>

                <div className="shrink-0">
                  {achievement.completed && !achievement.claimed ? (
                    <Button
                      variant="gold"
                      size="sm"
                      onClick={() => handleClaim(achievement)}
                    >
                      <Gift className="w-4 h-4 mr-1" />
                      +{achievement.reward}
                    </Button>
                  ) : achievement.claimed ? (
                    <span className="text-xs text-muted-foreground">Получено</span>
                  ) : (
                    <span className="text-xs text-mystic-gold font-medium">
                      +{achievement.reward}
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </PageTransition>
  );
};

export default Achievements;
