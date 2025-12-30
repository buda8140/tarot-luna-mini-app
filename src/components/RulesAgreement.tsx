import { motion } from 'framer-motion';
import { Moon, Sparkles, Shield, Heart, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { haptic } from '@/lib/telegram';

interface RulesAgreementProps {
  onAgree: () => void;
}

export const RulesAgreement: React.FC<RulesAgreementProps> = ({ onAgree }) => {
  const handleAgree = () => {
    haptic.success();
    onAgree();
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 py-12">
      {/* Decorative moon */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8 }}
        className="relative mb-8"
      >
        <div className="w-24 h-24 rounded-full bg-gradient-to-br from-mystic-gold/30 to-primary/20 flex items-center justify-center">
          <Moon className="w-12 h-12 text-mystic-gold" />
        </div>
        <motion.div
          animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="absolute inset-0 rounded-full bg-mystic-gold/10 blur-xl"
        />
      </motion.div>

      {/* Title */}
      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="text-2xl font-serif font-bold text-center mb-2"
      >
        Добро пожаловать в Таро Luna
      </motion.h1>
      
      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="text-muted-foreground text-center mb-8"
      >
        Перед началом, пожалуйста, ознакомьтесь с правилами
      </motion.p>

      {/* Rules */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mystic-card p-6 mb-8 max-w-md w-full space-y-4"
      >
        <div className="flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-mystic-gold shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium mb-1">О Таро</h3>
            <p className="text-sm text-muted-foreground">
              Таро — это инструмент самопознания и рефлексии. Карты не предсказывают будущее, 
              а помогают взглянуть на ситуацию под новым углом.
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Heart className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium mb-1">Ответственность</h3>
            <p className="text-sm text-muted-foreground">
              Интерпретации носят рекомендательный характер. Все важные решения принимаете 
              только вы сами.
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium mb-1">Возрастное ограничение</h3>
            <p className="text-sm text-muted-foreground">
              Сервис предназначен для лиц старше 18 лет.
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Shield className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium mb-1">Конфиденциальность</h3>
            <p className="text-sm text-muted-foreground">
              Ваши вопросы и расклады хранятся конфиденциально. Мы не передаём 
              персональные данные третьим лицам.
            </p>
          </div>
        </div>
      </motion.div>

      {/* Agreement button */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="w-full max-w-md"
      >
        <Button
          variant="gold"
          size="xl"
          className="w-full"
          onClick={handleAgree}
        >
          <Sparkles className="w-5 h-5 mr-2" />
          Согласен с правилами
        </Button>
        <p className="text-xs text-muted-foreground text-center mt-3">
          Нажимая кнопку, вы подтверждаете, что вам есть 18 лет и вы согласны с правилами использования
        </p>
      </motion.div>
    </div>
  );
};
