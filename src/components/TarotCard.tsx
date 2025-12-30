import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TarotCard as TarotCardType, CARD_BACK_URL } from '@/lib/tarot-data';
import { haptic } from '@/lib/telegram';
import { cn } from '@/lib/utils';

interface TarotCardProps {
  card: TarotCardType;
  index?: number;
  isRevealed?: boolean;
  onReveal?: () => void;
  size?: 'sm' | 'md' | 'lg';
  showMeaning?: boolean;
  isPremium?: boolean;
  delay?: number;
}

// Enhanced Magical Particles with more sparkle effects
const MagicalParticles = ({ 
  count = 20, 
  isGold = true,
  isPremium = false 
}: { 
  count?: number; 
  isGold?: boolean;
  isPremium?: boolean;
}) => {
  const particleCount = isPremium ? count * 2 : count;
  
  return (
    <div className="absolute inset-0 pointer-events-none overflow-visible z-50">
      {Array.from({ length: particleCount }).map((_, i) => {
        const angle = (i / particleCount) * 360 + Math.random() * 30;
        const distance = 50 + Math.random() * 80;
        const size = 2 + Math.random() * 4;
        const duration = 0.8 + Math.random() * 0.5;
        
        return (
          <motion.div
            key={i}
            className="absolute"
            style={{
              left: '50%',
              top: '50%',
              width: size,
              height: size,
              borderRadius: '50%',
              background: isGold 
                ? `radial-gradient(circle, hsl(45 100% 70%) 0%, hsl(45 90% 55%) 100%)`
                : `radial-gradient(circle, hsl(280 100% 80%) 0%, hsl(280 70% 50%) 100%)`,
              boxShadow: isGold
                ? '0 0 8px hsl(45 100% 60% / 0.8), 0 0 16px hsl(45 90% 55% / 0.5)'
                : '0 0 8px hsl(280 100% 70% / 0.8), 0 0 16px hsl(280 70% 60% / 0.5)',
            }}
            initial={{ 
              x: 0, 
              y: 0, 
              opacity: 1, 
              scale: 1,
            }}
            animate={{ 
              x: Math.cos(angle * Math.PI / 180) * distance,
              y: Math.sin(angle * Math.PI / 180) * distance,
              opacity: 0,
              scale: 0,
              rotate: Math.random() * 360,
            }}
            transition={{ 
              duration: duration, 
              ease: 'easeOut',
              delay: i * 0.02,
            }}
          />
        );
      })}
      
      {/* Additional sparkle stars for premium */}
      {isPremium && Array.from({ length: 8 }).map((_, i) => {
        const angle = (i / 8) * 360;
        const distance = 70 + Math.random() * 40;
        
        return (
          <motion.div
            key={`star-${i}`}
            className="absolute text-mystic-gold"
            style={{
              left: '50%',
              top: '50%',
              fontSize: '16px',
            }}
            initial={{ 
              x: 0, 
              y: 0, 
              opacity: 1, 
              scale: 1,
              rotate: 0,
            }}
            animate={{ 
              x: Math.cos(angle * Math.PI / 180) * distance,
              y: Math.sin(angle * Math.PI / 180) * distance,
              opacity: 0,
              scale: 0,
              rotate: 360,
            }}
            transition={{ 
              duration: 1,
              ease: 'easeOut',
              delay: i * 0.05,
            }}
          >
            ✦
          </motion.div>
        );
      })}
    </div>
  );
};

// Pulsing glow ring effect
const GlowRing = ({ isGold = true, isPremium = false }: { isGold?: boolean; isPremium?: boolean }) => (
  <motion.div
    className="absolute inset-0 rounded-lg -z-10"
    initial={{ scale: 0.8, opacity: 0 }}
    animate={{ 
      scale: [1, 1.15, 1.05],
      opacity: [0, 0.8, 0.5],
    }}
    transition={{ 
      duration: 1,
      times: [0, 0.4, 1],
      ease: 'easeOut',
    }}
    style={{
      background: isGold
        ? 'radial-gradient(ellipse at center, hsl(45 90% 55% / 0.5) 0%, transparent 70%)'
        : 'radial-gradient(ellipse at center, hsl(280 70% 50% / 0.5) 0%, transparent 70%)',
      filter: `blur(${isPremium ? 20 : 15}px)`,
    }}
  />
);

export const TarotCard = ({
  card,
  index = 0,
  isRevealed = false,
  onReveal,
  size = 'md',
  showMeaning = false,
  isPremium = false,
  delay = 0,
}: TarotCardProps) => {
  const [flipped, setFlipped] = useState(false);
  const [showParticles, setShowParticles] = useState(false);
  const [showGlow, setShowGlow] = useState(false);
  const hasFlippedRef = useRef(false);

  // Sync with external isRevealed prop
  useEffect(() => {
    if (isRevealed && !hasFlippedRef.current) {
      hasFlippedRef.current = true;
      setFlipped(true);
      setShowParticles(true);
      setShowGlow(true);
      
      // Trigger haptic feedback
      haptic.medium();
      
      setTimeout(() => setShowParticles(false), 1200);
    }
  }, [isRevealed]);

  const sizeClasses = {
    sm: 'w-16 h-24 sm:w-20 sm:h-32',
    md: 'w-24 h-36 sm:w-28 sm:h-44',
    lg: 'w-28 h-44 sm:w-36 sm:h-56',
  };

  const handleFlip = () => {
    if (!flipped) {
      haptic.medium();
      setFlipped(true);
      setShowParticles(true);
      setShowGlow(true);
      hasFlippedRef.current = true;
      
      setTimeout(() => setShowParticles(false), 1200);
      onReveal?.();
    }
  };

  const isGoldCard = !card.isReversed;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30, scale: 0.8, rotateZ: -5 }}
      animate={{ opacity: 1, y: 0, scale: 1, rotateZ: 0 }}
      transition={{ 
        delay: delay + index * 0.2, 
        duration: 0.6,
        type: 'spring',
        stiffness: 100,
      }}
      className="flex flex-col items-center gap-3"
    >
      <motion.div
        className={cn(
          'relative cursor-pointer',
          sizeClasses[size],
        )}
        onClick={handleFlip}
        style={{ perspective: '1200px' }}
        whileHover={!flipped ? { scale: 1.05, y: -5 } : undefined}
        whileTap={!flipped ? { scale: 0.98 } : undefined}
      >
        {/* Particles effect on flip */}
        <AnimatePresence>
          {showParticles && (
            <MagicalParticles 
              count={24} 
              isGold={isGoldCard} 
              isPremium={isPremium}
            />
          )}
        </AnimatePresence>

        {/* Glow ring effect */}
        <AnimatePresence>
          {showGlow && (
            <GlowRing isGold={isGoldCard} isPremium={isPremium} />
          )}
        </AnimatePresence>

        {/* Premium border wrapper */}
        {isPremium && (
          <motion.div
            className="absolute -inset-1 rounded-xl z-0"
            animate={flipped ? {
              boxShadow: [
                '0 0 20px hsl(45 90% 55% / 0.4)',
                '0 0 40px hsl(45 90% 55% / 0.6)',
                '0 0 20px hsl(45 90% 55% / 0.4)',
              ],
            } : undefined}
            transition={{ duration: 2, repeat: Infinity }}
            style={{
              background: 'linear-gradient(135deg, hsl(45 90% 55%) 0%, hsl(35 85% 45%) 50%, hsl(45 90% 55%) 100%)',
            }}
          />
        )}

        <motion.div
          className="relative w-full h-full z-10"
          animate={{ rotateY: flipped ? 180 : 0 }}
          transition={{ 
            duration: 0.8, 
            ease: [0.25, 0.1, 0.25, 1],
          }}
          style={{ transformStyle: 'preserve-3d' }}
        >
          {/* Card Back */}
          <div
            className={cn(
              'absolute inset-0 rounded-lg overflow-hidden',
              'border-2 border-mystic-gold/40',
              'shadow-lg',
            )}
            style={{ backfaceVisibility: 'hidden' }}
          >
            <img
              src={CARD_BACK_URL}
              alt="Card back"
              className="w-full h-full object-cover"
              loading="eager"
            />
            {/* Shimmer effect on back */}
            <motion.div
              className="absolute inset-0"
              animate={{
                background: [
                  'linear-gradient(45deg, transparent 30%, hsl(45 90% 70% / 0.1) 50%, transparent 70%)',
                  'linear-gradient(45deg, transparent 30%, hsl(45 90% 70% / 0.2) 50%, transparent 70%)',
                ],
                backgroundPosition: ['-200% 0', '200% 0'],
              }}
              transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
            />
          </div>

          {/* Card Front */}
          <div
            className={cn(
              'absolute inset-0 rounded-lg overflow-hidden',
              'border-2',
              card.isReversed 
                ? 'border-mystic-violet/60' 
                : 'border-mystic-gold/60',
              isPremium && flipped && 'shadow-[0_0_40px_hsl(45_90%_55%_/_0.5)]',
            )}
            style={{ 
              backfaceVisibility: 'hidden',
              transform: 'rotateY(180deg)',
            }}
          >
            <img
              src={card.imageUrl}
              alt={card.nameRu}
              className={cn(
                'w-full h-full object-cover',
                card.isReversed && 'rotate-180',
              )}
              loading="lazy"
            />
            
            {/* Reversed indicator */}
            {card.isReversed && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="absolute bottom-1 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-mystic-violet/90 rounded text-xs font-medium text-white"
              >
                Перевёрнутая
              </motion.div>
            )}
            
            {/* Premium shine effect */}
            {isPremium && (
              <motion.div
                className="absolute inset-0 pointer-events-none"
                animate={{
                  background: [
                    'linear-gradient(120deg, transparent 0%, hsl(45 100% 70% / 0.1) 50%, transparent 100%)',
                    'linear-gradient(120deg, transparent 0%, hsl(45 100% 70% / 0.2) 50%, transparent 100%)',
                  ],
                  backgroundPosition: ['-100% 0', '200% 0'],
                }}
                transition={{ duration: 2, repeat: Infinity, repeatDelay: 1 }}
              />
            )}
          </div>
        </motion.div>
      </motion.div>

      {/* Card meaning */}
      <AnimatePresence>
        {flipped && showMeaning && (
          <motion.div
            initial={{ opacity: 0, y: 15, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.9 }}
            transition={{ delay: 0.4, duration: 0.5, type: 'spring' }}
            className="text-center max-w-[140px] sm:max-w-[160px]"
          >
            <motion.p 
              className={cn(
                'text-xs sm:text-sm font-serif font-bold mb-1',
                card.isReversed ? 'text-mystic-violet' : 'text-mystic-gold',
              )}
              animate={isPremium ? {
                textShadow: [
                  '0 0 10px hsl(45 90% 55% / 0.5)',
                  '0 0 20px hsl(45 90% 55% / 0.8)',
                  '0 0 10px hsl(45 90% 55% / 0.5)',
                ],
              } : undefined}
              transition={{ duration: 2, repeat: Infinity }}
            >
              {card.nameRu}
            </motion.p>
            <p className="text-xs text-muted-foreground leading-tight">
              {card.isReversed ? card.meaningReversed : card.meaning}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};