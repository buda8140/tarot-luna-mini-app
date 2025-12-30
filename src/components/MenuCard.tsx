import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { haptic } from '@/lib/telegram';

interface MenuCardProps {
  icon: string;
  title: string;
  description?: string;
  onClick?: () => void;
  isPremium?: boolean;
  disabled?: boolean;
  className?: string;
}

export const MenuCard = ({
  icon,
  title,
  description,
  onClick,
  isPremium = false,
  disabled = false,
  className,
}: MenuCardProps) => {
  const handleClick = () => {
    if (!disabled && onClick) {
      haptic.light();
      onClick();
    }
  };

  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      onClick={handleClick}
      disabled={disabled}
      className={cn(
        'w-full p-4 rounded-xl text-left transition-all duration-300',
        'bg-card/60 backdrop-blur-sm border border-border/50',
        'hover:bg-card/80 hover:border-border',
        isPremium && 'premium-border',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      <div className="flex items-center gap-3">
        <span className="text-2xl">{icon}</span>
        <div className="flex-1 min-w-0">
          <h3 className={cn(
            'font-medium text-foreground truncate',
            isPremium && 'gold-text'
          )}>
            {title}
          </h3>
          {description && (
            <p className="text-sm text-muted-foreground truncate">
              {description}
            </p>
          )}
        </div>
        {isPremium && (
          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-mystic-gold/20 text-mystic-gold">
            Premium
          </span>
        )}
      </div>
    </motion.button>
  );
};
