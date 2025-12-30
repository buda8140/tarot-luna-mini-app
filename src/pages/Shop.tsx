import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Crown, Sparkles, Check, Loader2 } from 'lucide-react';
import { PageTransition } from '@/components/PageTransition';
import { Button } from '@/components/ui/button';
import { haptic, openLink, getUser } from '@/lib/telegram';
import { getRates, createPayment, PaymentPackage } from '@/lib/api';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

const features = [
  'Подробные толкования от AI',
  'Учёт контекста и истории',
  'Персональные советы',
  'Расклады на 4+ карт',
  'Приоритетная поддержка',
];

const Shop = () => {
  const navigate = useNavigate();
  const user = getUser();
  const [packages, setPackages] = useState<PaymentPackage[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadRates();
  }, []);

  const loadRates = async () => {
    try {
      const rates = await getRates();
      // Добавляем метки к тарифам
      const enrichedRates = rates.map((rate, index) => {
        // Определяем свойства в зависимости от package_key
        if (rate.package_key === 'test_5') {
          return {
            ...rate,
            name: '🧪 Тестовый',
            popular: false,
            discount: undefined,
          };
        }
        
        const regularIndex = rates.filter(r => r.package_key !== 'test_5').indexOf(rate);
        return {
          ...rate,
          name: rate.name || (regularIndex === 0 ? 'Начальный' : regularIndex === 1 ? 'Популярный' : 'Максимальный'),
          popular: regularIndex === 1,
          discount: regularIndex === 2 ? '-30%' : regularIndex === 1 ? '-17%' : undefined,
        };
      });
      setPackages(enrichedRates);
    } catch (error) {
      console.error('Error loading rates:', error);
      // Fallback тарифы с тестовым
      setPackages([
        { package_key: 'test_5', name: '🧪 Тестовый', requests: 5, price: 2 },
        { package_key: 'buy_1', name: 'Начальный', requests: 5, price: 100 },
        { package_key: 'buy_2', name: 'Популярный', requests: 15, price: 250, popular: true, discount: '-17%' },
        { package_key: 'buy_3', name: 'Максимальный', requests: 35, price: 500, discount: '-30%' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePurchase = async (pkg: PaymentPackage) => {
    haptic.medium();
    
    try {
      toast.info('Создаём ссылку на оплату...');
      
      // Используем API для создания платежа
      const result = await createPayment(pkg.package_key);
      
      if (!result.success || !result.payment?.url) {
        toast.error(result.error || 'Не удалось создать ссылку на оплату');
        return;
      }
      
      console.log('Payment created:', result.payment);
      toast.success('Переходим к оплате...');
      
      // Открываем ссылку
      openLink(result.payment.url);
    } catch (error) {
      console.error('Payment error:', error);
      toast.error('Ошибка при создании платежа');
    }
  };

  if (isLoading) {
    return (
      <PageTransition>
        <div className="flex items-center justify-center min-h-[50vh]">
          <Loader2 className="w-8 h-8 animate-spin text-mystic-gold" />
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="px-4 pt-6 pb-24">
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
              <Crown className="w-5 h-5 text-mystic-gold" />
              Магазин
            </h1>
            <p className="text-sm text-muted-foreground">
              Премиум запросы для глубоких раскладов
            </p>
          </div>
        </motion.div>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mystic-card p-5 mb-6"
        >
          <h2 className="font-medium mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-mystic-gold" />
            Преимущества Premium
          </h2>
          <ul className="space-y-2">
            {features.map((feature, index) => (
              <motion.li
                key={feature}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 + index * 0.05 }}
                className="flex items-center gap-2 text-sm text-muted-foreground"
              >
                <Check className="w-4 h-4 text-mystic-gold shrink-0" />
                {feature}
              </motion.li>
            ))}
          </ul>
        </motion.div>

        {/* Packages */}
        <div className="space-y-4">
          {packages.map((pkg, index) => (
            <motion.div
              key={pkg.package_key}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + index * 0.1 }}
              className={cn(
                'relative overflow-hidden rounded-xl p-5',
                'bg-card/60 backdrop-blur-sm border',
                pkg.popular
                  ? 'border-mystic-gold/50 shadow-[0_0_20px_hsl(45_90%_55%/0.2)]'
                  : 'border-border/50'
              )}
            >
              {pkg.popular && (
                <div className="absolute top-0 right-0 px-3 py-1 bg-mystic-gold text-secondary-foreground text-xs font-bold rounded-bl-lg">
                  ХИТ
                </div>
              )}
              {pkg.discount && (
                <div className="absolute top-0 left-0 px-3 py-1 bg-destructive text-destructive-foreground text-xs font-bold rounded-br-lg">
                  {pkg.discount}
                </div>
              )}

              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-medium text-lg">{pkg.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {pkg.requests} премиум запросов
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold gold-text">{pkg.price} ₽</p>
                  <p className="text-xs text-muted-foreground">
                    {(pkg.price / pkg.requests).toFixed(0)} ₽/запрос
                  </p>
                </div>
              </div>

              <Button
                variant={pkg.popular ? 'gold' : 'mystic'}
                size="lg"
                className="w-full"
                onClick={() => handlePurchase(pkg)}
              >
                <Crown className="w-4 h-4 mr-2" />
                Купить
              </Button>
            </motion.div>
          ))}
        </div>

        {/* Note */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center text-xs text-muted-foreground mt-6"
        >
          Оплата через YooMoney. Запросы начисляются автоматически после подтверждения платежа.
        </motion.p>

        {/* Payment info */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mystic-card p-4 mt-4"
        >
          <p className="text-xs text-muted-foreground text-center">
            💳 После оплаты запросы будут начислены автоматически в течение 1-2 минут.
            Если запросы не появились — напишите в поддержку.
          </p>
        </motion.div>
      </div>
    </PageTransition>
  );
};

export default Shop;