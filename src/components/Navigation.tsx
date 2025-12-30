import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Home, Sparkles, User, ShoppingCart, History } from 'lucide-react';
import { cn } from '@/lib/utils';
import { haptic } from '@/lib/telegram';

const navItems = [
  { path: '/', icon: Home, label: 'Главная' },
  { path: '/reading', icon: Sparkles, label: 'Расклад' },
  { path: '/profile', icon: User, label: 'Профиль' },
  { path: '/shop', icon: ShoppingCart, label: 'Магазин' },
  { path: '/history', icon: History, label: 'История' },
];

export const Navigation = () => {
  const location = useLocation();

  return (
    <motion.nav
      initial={{ y: 100 }}
      animate={{ y: 0 }}
      className="fixed bottom-0 left-0 right-0 z-50 pb-safe"
    >
      <div className="mx-4 mb-4">
        <div className="flex items-center justify-around px-2 py-3 rounded-2xl bg-card/80 backdrop-blur-lg border border-border/50 shadow-lg">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => haptic.selection()}
                className="relative flex flex-col items-center gap-1 px-4 py-1"
              >
                {isActive && (
                  <motion.div
                    layoutId="nav-indicator"
                    className="absolute -top-1 w-8 h-1 rounded-full bg-gradient-to-r from-primary to-accent"
                    transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                  />
                )}
                <Icon
                  className={cn(
                    'w-5 h-5 transition-colors duration-200',
                    isActive ? 'text-primary' : 'text-muted-foreground'
                  )}
                />
                <span
                  className={cn(
                    'text-[10px] font-medium transition-colors duration-200',
                    isActive ? 'text-foreground' : 'text-muted-foreground'
                  )}
                >
                  {item.label}
                </span>
              </NavLink>
            );
          })}
        </div>
      </div>
    </motion.nav>
  );
};
