import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Calendar, CreditCard, ChevronRight, Sparkles, Loader2, CheckCircle, Clock, XCircle, Eye, Moon } from 'lucide-react';
import { PageTransition } from '@/components/PageTransition';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { getHistory, HistoryItem, PaymentItem } from '@/lib/api';

const History = () => {
  const navigate = useNavigate();
  const [expandedReading, setExpandedReading] = useState<string | null>(null);
  const [readings, setReadings] = useState<HistoryItem[]>([]);
  const [payments, setPayments] = useState<PaymentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedReading, setSelectedReading] = useState<HistoryItem | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setIsLoading(true);
    try {
      console.log('[History] Loading history...');
      const data = await getHistory(0, 50);
      console.log('[History] Received data:', data);
      
      if (data.error) {
        console.error('[History] Error:', data.error);
      }
      
      setReadings(data.history || []);
      setPayments(data.payments || []);
      
      console.log('[History] Readings:', data.history?.length || 0, 'Payments:', data.payments?.length || 0);
    } catch (error) {
      console.error('[History] Error loading:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getReadingTypeEmoji = (type: string): string => {
    const types: Record<string, string> = {
      'classic': '🔮',
      'love': '💖',
      'career': '💼',
      'situation': '⭐',
      'daily': '🌙',
      'custom': '✨',
    };
    return types[type?.toLowerCase()] || '🔮';
  };

  const getReadingTypeName = (type: string): string => {
    const types: Record<string, string> = {
      'classic': 'Классический',
      'love': 'На отношения',
      'career': 'На карьеру',
      'situation': 'На ситуацию',
      'daily': 'Карта дня',
      'custom': 'Свои карты',
    };
    return types[type?.toLowerCase()] || type || 'Классический';
  };

  const parseCards = (cardsStr: string): string[] => {
    try {
      return JSON.parse(cardsStr);
    } catch {
      return cardsStr.split(',').map(c => c.trim());
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
      case 'confirmed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'failed':
      case 'cancelled':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
      case 'confirmed':
        return 'Оплачено';
      case 'pending':
        return 'В обработке';
      case 'failed':
        return 'Ошибка';
      case 'cancelled':
        return 'Отменено';
      default:
        return status;
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
      <div className="px-3 pt-4 pb-20">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 mb-4"
        >
          <button onClick={() => navigate(-1)} className="p-1.5 rounded-lg hover:bg-muted transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="text-lg font-serif font-bold">История</h1>
        </motion.div>

        <Tabs defaultValue="readings" className="w-full">
          <TabsList className="w-full bg-card/60 border border-border/50 h-9">
            <TabsTrigger value="readings" className="flex-1 text-xs">
              <Sparkles className="w-3 h-3 mr-1.5" />
              Расклады
            </TabsTrigger>
            <TabsTrigger value="payments" className="flex-1 text-xs">
              <CreditCard className="w-3 h-3 mr-1.5" />
              Покупки
            </TabsTrigger>
          </TabsList>

          <TabsContent value="readings" className="mt-3 space-y-2">
            {readings.length === 0 ? (
              <div className="mystic-card p-6 text-center">
                <Moon className="w-10 h-10 mx-auto mb-3 text-muted-foreground opacity-50" />
                <p className="text-sm text-muted-foreground mb-1">Вы ещё не делали раскладов 🌙</p>
                <p className="text-xs text-muted-foreground/70">Начните свой первый путь!</p>
                <button
                  onClick={() => navigate('/reading')}
                  className="mt-3 px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-xs"
                >
                  Сделать расклад
                </button>
              </div>
            ) : (
              readings.map((reading, index) => (
                <motion.div
                  key={reading.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.03 }}
                  className="mystic-card overflow-hidden"
                >
                  <button
                    onClick={() => setSelectedReading(reading)}
                    className="w-full p-3 text-left"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2 flex-1 min-w-0">
                        <span className="text-xl flex-shrink-0">{getReadingTypeEmoji(reading.reading_type)}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                            <span className="font-medium text-xs">№{readings.length - index}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/20 text-primary">
                              {getReadingTypeName(reading.reading_type)}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground truncate">{reading.question}</p>
                          <div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-muted-foreground">
                            <Calendar className="w-2.5 h-2.5" />
                            {format(new Date(reading.timestamp || reading.created_at || new Date()), 'd MMM, HH:mm', { locale: ru })}
                          </div>
                        </div>
                      </div>
                      <Eye className="w-4 h-4 text-primary flex-shrink-0" />
                    </div>
                  </button>
                </motion.div>
              ))
            )}
          </TabsContent>

          <TabsContent value="payments" className="mt-3 space-y-2">
            {payments.length === 0 ? (
              <div className="mystic-card p-6 text-center">
                <CreditCard className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">История покупок пуста</p>
              </div>
            ) : (
              payments.map((payment, index) => (
                <motion.div
                  key={payment.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.03 }}
                  className="mystic-card p-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        {getStatusIcon(payment.status)}
                        <span className="text-xs font-medium">{payment.requests} запросов</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                        <span>{payment.amount} ₽</span>
                        <span>•</span>
                        <span>{getStatusText(payment.status)}</span>
                        <span>•</span>
                        <span>{format(new Date(payment.timestamp), 'd MMM', { locale: ru })}</span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </TabsContent>
        </Tabs>

        {/* Модальное окно для просмотра расклада */}
        <Dialog open={!!selectedReading} onOpenChange={() => setSelectedReading(null)}>
          <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto bg-background border-border mx-2">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-base">
                <span className="text-lg">{getReadingTypeEmoji(selectedReading?.reading_type || '')}</span>
                {getReadingTypeName(selectedReading?.reading_type || '')}
              </DialogTitle>
            </DialogHeader>
            
            {selectedReading && (
              <div className="space-y-3 mt-1">
                {/* Дата */}
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Calendar className="w-3 h-3" />
                  {format(new Date(selectedReading.timestamp || selectedReading.created_at || new Date()), 'd MMMM yyyy, HH:mm', { locale: ru })}
                </div>

                {/* Вопрос */}
                <div className="p-2.5 rounded-lg bg-muted/50">
                  <p className="text-xs font-medium mb-0.5">Ваш вопрос:</p>
                  <p className="text-xs text-muted-foreground">{selectedReading.question}</p>
                </div>

                {/* Карты */}
                <div>
                  <p className="text-xs font-medium mb-1.5">Выпавшие карты:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {parseCards(selectedReading.cards).map((card, i) => (
                      <span key={i} className="px-2 py-1 text-[10px] rounded-full bg-mystic-gold/20 text-mystic-gold border border-mystic-gold/30">
                        {card}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Толкование */}
                {selectedReading.response && (
                  <div>
                    <p className="text-xs font-medium mb-1.5">Толкование:</p>
                    <div className="p-2.5 rounded-lg bg-card border border-border/50 max-h-48 overflow-y-auto">
                      <p className="text-xs whitespace-pre-wrap leading-relaxed">{selectedReading.response}</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </PageTransition>
  );
};

export default History;