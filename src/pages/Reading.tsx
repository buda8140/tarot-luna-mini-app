import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Sparkles, Crown, RefreshCw, ChevronLeft, ChevronRight, Home } from 'lucide-react';
import { PageTransition } from '@/components/PageTransition';
import { TarotCard } from '@/components/TarotCard';
import { BalanceDisplay } from '@/components/BalanceDisplay';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { haptic } from '@/lib/telegram';
import { generateRandomCards, READING_TYPES, ReadingType, TarotCard as TarotCardType } from '@/lib/tarot-data';
import { createReading, cleanInterpretation, paginateText } from '@/lib/api';
import { useUser } from '@/contexts/UserContext';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

type ReadingStep = 'question' | 'cards' | 'reveal' | 'result';

const Reading = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const readingType = (searchParams.get('type') as ReadingType) || 'classic';
  
  // Используем контекст пользователя для реальных данных
  const { user, spendRequest, refreshUser } = useUser();

  const [step, setStep] = useState<ReadingStep>('question');
  const [question, setQuestion] = useState('');
  const [cardCount, setCardCount] = useState(3);
  const [cards, setCards] = useState<TarotCardType[]>([]);
  const [revealedCards, setRevealedCards] = useState<Set<number>>(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [interpretation, setInterpretation] = useState('');
  const [interpretationPages, setInterpretationPages] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const readingInfo = READING_TYPES[readingType];
  const isPremium = readingType === 'custom';
  const isRandom = readingType === 'random';

  // Auto-reveal cards sequentially when entering reveal step
  useEffect(() => {
    if (step === 'reveal' && cards.length > 0) {
      let currentIndex = 0;
      const revealInterval = setInterval(() => {
        if (currentIndex < cards.length) {
          setRevealedCards(prev => {
            const newSet = new Set(prev);
            newSet.add(currentIndex);
            return newSet;
          });
          haptic.medium();
          currentIndex++;
        } else {
          clearInterval(revealInterval);
          // Start generating interpretation after all cards revealed
          setTimeout(() => {
            generateInterpretation();
          }, 800);
        }
      }, 700);

      return () => clearInterval(revealInterval);
    }
  }, [step, cards.length]);

  const handleStartReading = async () => {
    if (!isRandom && question.trim().length < 5) {
      haptic.warning();
      toast.error('Вопрос слишком короткий');
      return;
    }

    // Проверка на запрещённые слова
    const forbidden = /болезнь|смерть|убийство|суд|тюрьма|арест|катастрофа|теракт|горе|депрессия|суицид|наркотик/i;
    if (forbidden.test(question)) {
      haptic.error();
      toast.error('Вопрос содержит запрещённые темы');
      return;
    }

    haptic.medium();
    const generatedCards = generateRandomCards(cardCount);
    setCards(generatedCards);
    setStep('cards');
  };

  const handleRevealAll = () => {
    haptic.medium();
    setRevealedCards(new Set());
    setStep('reveal');
  };

  const handleCardReveal = (index: number) => {
    const newRevealed = new Set(revealedCards);
    newRevealed.add(index);
    setRevealedCards(newRevealed);
  };

  const generateInterpretation = async () => {
    setIsGenerating(true);
    haptic.success();

    // Определяем тип запроса: премиум если 4+ карт или премиум тип расклада
    const needsPremium = cardCount >= 4 || isPremium;

    // Проверяем баланс
    if (needsPremium && (!user || user.premium_requests <= 0)) {
      if (!user || user.requests_left <= 0) {
        toast.error('Недостаточно запросов. Пополните баланс!');
        navigate('/shop');
        setIsGenerating(false);
        return;
      }
    } else if (!needsPremium && (!user || user.requests_left <= 0)) {
      if (!user || user.premium_requests <= 0) {
        toast.error('Недостаточно запросов. Пополните баланс!');
        navigate('/shop');
        setIsGenerating(false);
        return;
      }
    }

    try {
      // Вызываем реальный API для получения толкования
      // Передаем карты, которые видит пользователь на экране
      const result = await createReading(
        question || 'Что мне нужно знать сегодня?',
        cardCount,
        readingType,
        needsPremium,
        cards // Передаем выбранные карты
      );

      if (result.success && result.reading) {
        // Списываем запрос после успешного расклада
        spendRequest(needsPremium);
        
        // Очищаем текст от лишнего форматирования
        const cleanText = cleanInterpretation(result.reading.interpretation);
        setInterpretation(cleanText);
        
        // Разбиваем на страницы если текст длинный
        const pages = paginateText(cleanText, 1500);
        setInterpretationPages(pages);
        setCurrentPage(0);
        
        toast.success('Расклад сохранён в историю');
        setStep('result');
      } else {
        // Ошибка API - показываем сообщение
        toast.error(result.error || 'Ошибка сервера. Запустите бэкенд!');
        haptic.error();
      }
    } catch (error) {
      console.error('Error generating interpretation:', error);
      toast.error('Ошибка подключения к серверу');
      haptic.error();
    }

    setIsGenerating(false);
  };

  const handleNewReading = () => {
    haptic.light();
    setStep('question');
    setQuestion('');
    setCards([]);
    setRevealedCards(new Set());
    setInterpretation('');
    setInterpretationPages([]);
    setCurrentPage(0);
  };

  const handleNextPage = () => {
    if (currentPage < interpretationPages.length - 1) {
      haptic.selection();
      setCurrentPage(currentPage + 1);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 0) {
      haptic.selection();
      setCurrentPage(currentPage - 1);
    }
  };

  const cardCountOptions = [1, 2, 3, 4, 5];

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
              {readingInfo.icon} {readingInfo.name}
              {isPremium && <Crown className="w-4 h-4 text-mystic-gold" />}
            </h1>
            <p className="text-sm text-muted-foreground">{readingInfo.description}</p>
          </div>
        </motion.div>

        <AnimatePresence mode="wait">
          {/* Question Step */}
          {step === 'question' && (
            <motion.div
              key="question"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-6"
            >
              {!isRandom && (
                <div className="space-y-3">
                  <label className="text-sm font-medium">Твой вопрос</label>
                  <Textarea
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Например: Что меня ждёт в ближайшем месяце?"
                    className="min-h-[120px] bg-card/60 border-border/50 resize-none"
                    maxLength={300}
                  />
                  <p className="text-xs text-muted-foreground text-right">
                    {question.length}/300
                  </p>
                </div>
              )}

              <div className="space-y-3">
                <label className="text-sm font-medium">Количество карт</label>
                <div className="flex gap-2">
                  {cardCountOptions.map((count) => (
                    <button
                      key={count}
                      onClick={() => {
                        haptic.selection();
                        setCardCount(count);
                      }}
                      className={cn(
                        'flex-1 py-3 rounded-lg font-medium transition-all',
                        'border-2',
                        cardCount === count
                          ? 'border-primary bg-primary/20 text-primary'
                          : 'border-border/50 bg-card/60 hover:border-border'
                      )}
                    >
                      {count}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  {cardCount >= 4 ? '⭐ Расклад 4+ карт использует премиум-запрос' : '✨ Бесплатный расклад'}
                </p>
              </div>

              <Button
                variant="mystic"
                size="xl"
                className="w-full"
                onClick={handleStartReading}
                disabled={!isRandom && question.trim().length < 5}
              >
                <Sparkles className="w-5 h-5 mr-2" />
                Разложить карты
              </Button>
            </motion.div>
          )}

          {/* Cards Display Step */}
          {step === 'cards' && (
            <motion.div
              key="cards"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="space-y-6"
            >
              <div className="text-center mb-4">
                <p className="text-muted-foreground">
                  Карты выбраны! Нажми чтобы открыть...
                </p>
              </div>

              <div className="flex flex-wrap justify-center gap-2 sm:gap-4 min-h-[180px]">
                {cards.map((card, index) => (
                  <TarotCard
                    key={card.id}
                    card={card}
                    index={index}
                    isRevealed={false}
                    size="sm"
                    isPremium={isPremium}
                  />
                ))}
              </div>

              <Button
                variant="gold"
                size="xl"
                className="w-full"
                onClick={handleRevealAll}
              >
                <Sparkles className="w-5 h-5 mr-2" />
                Открыть все карты
              </Button>
            </motion.div>
          )}

          {/* Reveal Step */}
          {step === 'reveal' && (
            <motion.div
              key="reveal"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              <div className="flex flex-wrap justify-center gap-3 sm:gap-6">
                {cards.map((card, index) => (
                  <TarotCard
                    key={card.id}
                    card={card}
                    index={index}
                    isRevealed={revealedCards.has(index)}
                    onReveal={() => handleCardReveal(index)}
                    size="md"
                    showMeaning
                    isPremium={isPremium}
                    delay={index * 0.6}
                  />
                ))}
              </div>

              {isGenerating && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-8"
                >
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                    className="inline-block mb-4"
                  >
                    <Sparkles className="w-8 h-8 text-mystic-gold" />
                  </motion.div>
                  <p className="text-muted-foreground">Читаю послание карт...</p>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* Result Step */}
          {step === 'result' && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              <div className="flex flex-wrap justify-center gap-2 sm:gap-4 mb-4">
                {cards.map((card, index) => (
                  <TarotCard
                    key={card.id}
                    card={card}
                    index={index}
                    isRevealed
                    size="sm"
                    isPremium={isPremium}
                  />
                ))}
              </div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="mystic-card p-6"
              >
                <h2 className="text-lg font-serif font-bold mb-4 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-mystic-gold" />
                  Толкование
                  {interpretationPages.length > 1 && (
                    <span className="text-sm font-normal text-muted-foreground ml-auto">
                      {currentPage + 1}/{interpretationPages.length}
                    </span>
                  )}
                </h2>
                <div className="prose prose-invert prose-sm max-w-none">
                  {(interpretationPages[currentPage] || interpretation)
                    .split('\n')
                    .map((line, i) => (
                      <p key={i} className="text-foreground/90 leading-relaxed mb-2">
                        {line}
                      </p>
                    ))}
                </div>

                {/* Pagination controls */}
                {interpretationPages.length > 1 && (
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-border/30">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handlePrevPage}
                      disabled={currentPage === 0}
                      className="gap-1"
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Назад
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      Страница {currentPage + 1} из {interpretationPages.length}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleNextPage}
                      disabled={currentPage === interpretationPages.length - 1}
                      className="gap-1"
                    >
                      Далее
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                )}
              </motion.div>

              <div className="flex gap-3">
                <Button
                  variant="glass"
                  size="lg"
                  className="flex-1"
                  onClick={handleNewReading}
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Новый расклад
                </Button>
                <Button
                  variant="mystic"
                  size="lg"
                  className="flex-1"
                  onClick={() => navigate('/')}
                >
                  <Home className="w-4 h-4 mr-2" />
                  На главную
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  );
};

export default Reading;