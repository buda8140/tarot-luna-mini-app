import { motion } from 'framer-motion';
import { Sparkles, Crown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUser } from '@/contexts/UserContext';

interface BalanceDisplayProps {
  freeRequests?: number;
  premiumRequests?: number;
  className?: string;
}

export const BalanceDisplay = ({
  freeRequests,
  premiumRequests,
  className,
}: BalanceDisplayProps) => {
  const { user } = useUser();
  
  // Используем данные из контекста если не переданы напрямую
  const free = freeRequests ?? user?.requests_left ?? 0;
  const premium = premiumRequests ?? user?.premium_requests ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex items-center gap-3 px-4 py-2 rounded-xl',
        'bg-card/60 backdrop-blur-sm border border-border/50',
        className
      )}
    >
      <div className="flex items-center gap-1.5">
        <Sparkles className="w-4 h-4 text-primary" />
        <span className="text-sm font-medium">{free}</span>
      </div>
      <div className="w-px h-4 bg-border" />
      <div className="flex items-center gap-1.5">
        <Crown className="w-4 h-4 text-mystic-gold" />
        <span className="text-sm font-medium text-mystic-gold">{premium}</span>
      </div>
    </motion.div>
  );
};
