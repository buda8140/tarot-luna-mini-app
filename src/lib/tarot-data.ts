// Полная колода Таро Rider-Waite (78 карт)
// Изображения из локальной папки /assets/cards/

export interface TarotCard {
  id: number;
  name: string;
  nameRu: string;
  arcana: 'major' | 'minor';
  suit?: 'wands' | 'cups' | 'swords' | 'pentacles';
  meaning: string;
  meaningReversed: string;
  imageUrl: string;
  isReversed?: boolean;
}

// URL рубашки карты
export const CARD_BACK_URL = '/assets/cards/back.jpg';

// Мажорные арканы (22 карты)
export const MAJOR_ARCANA: TarotCard[] = [
  { id: 0, name: 'The Fool', nameRu: 'Шут', arcana: 'major', meaning: 'Новые начинания, спонтанность, свобода духа', meaningReversed: 'Безрассудство, риск, наивность', imageUrl: '/assets/cards/00.jpg' },
  { id: 1, name: 'The Magician', nameRu: 'Маг', arcana: 'major', meaning: 'Сила воли, мастерство, проявление желаний', meaningReversed: 'Манипуляции, нереализованный потенциал', imageUrl: '/assets/cards/01.jpg' },
  { id: 2, name: 'The High Priestess', nameRu: 'Верховная Жрица', arcana: 'major', meaning: 'Интуиция, тайны, внутренний голос', meaningReversed: 'Скрытые мотивы, поверхностность', imageUrl: '/assets/cards/02.jpg' },
  { id: 3, name: 'The Empress', nameRu: 'Императрица', arcana: 'major', meaning: 'Изобилие, плодородие, женственность', meaningReversed: 'Творческий застой, зависимость', imageUrl: '/assets/cards/03.jpg' },
  { id: 4, name: 'The Emperor', nameRu: 'Император', arcana: 'major', meaning: 'Власть, структура, отцовская фигура', meaningReversed: 'Тирания, негибкость, доминирование', imageUrl: '/assets/cards/04.jpg' },
  { id: 5, name: 'The Hierophant', nameRu: 'Иерофант', arcana: 'major', meaning: 'Традиции, духовное руководство, образование', meaningReversed: 'Догматизм, бунтарство, нетрадиционность', imageUrl: '/assets/cards/05.jpg' },
  { id: 6, name: 'The Lovers', nameRu: 'Влюблённые', arcana: 'major', meaning: 'Любовь, гармония, важный выбор', meaningReversed: 'Дисгармония, неверный выбор, дисбаланс', imageUrl: '/assets/cards/06.jpg' },
  { id: 7, name: 'The Chariot', nameRu: 'Колесница', arcana: 'major', meaning: 'Победа, решительность, самоконтроль', meaningReversed: 'Потеря контроля, агрессия, препятствия', imageUrl: '/assets/cards/07.jpg' },
  { id: 8, name: 'Strength', nameRu: 'Сила', arcana: 'major', meaning: 'Внутренняя сила, храбрость, терпение', meaningReversed: 'Слабость, неуверенность, сомнения', imageUrl: '/assets/cards/08.jpg' },
  { id: 9, name: 'The Hermit', nameRu: 'Отшельник', arcana: 'major', meaning: 'Самопознание, одиночество, мудрость', meaningReversed: 'Изоляция, одиночество, отверженность', imageUrl: '/assets/cards/09.jpg' },
  { id: 10, name: 'Wheel of Fortune', nameRu: 'Колесо Фортуны', arcana: 'major', meaning: 'Судьба, удача, перемены к лучшему', meaningReversed: 'Неудача, сопротивление переменам', imageUrl: '/assets/cards/10.jpg' },
  { id: 11, name: 'Justice', nameRu: 'Справедливость', arcana: 'major', meaning: 'Справедливость, истина, баланс', meaningReversed: 'Несправедливость, нечестность, предвзятость', imageUrl: '/assets/cards/11.jpg' },
  { id: 12, name: 'The Hanged Man', nameRu: 'Повешенный', arcana: 'major', meaning: 'Жертва, новый взгляд, отпускание', meaningReversed: 'Застой, сопротивление, эгоизм', imageUrl: '/assets/cards/12.jpg' },
  { id: 13, name: 'Death', nameRu: 'Смерть', arcana: 'major', meaning: 'Трансформация, конец цикла, обновление', meaningReversed: 'Сопротивление переменам, застой', imageUrl: '/assets/cards/13.jpg' },
  { id: 14, name: 'Temperance', nameRu: 'Умеренность', arcana: 'major', meaning: 'Баланс, терпение, гармония', meaningReversed: 'Дисбаланс, крайности, нетерпение', imageUrl: '/assets/cards/14.jpg' },
  { id: 15, name: 'The Devil', nameRu: 'Дьявол', arcana: 'major', meaning: 'Зависимость, материализм, искушение', meaningReversed: 'Освобождение, преодоление страхов', imageUrl: '/assets/cards/15.jpg' },
  { id: 16, name: 'The Tower', nameRu: 'Башня', arcana: 'major', meaning: 'Разрушение, внезапные перемены, откровение', meaningReversed: 'Избежание катастрофы, страх перемен', imageUrl: '/assets/cards/16.jpg' },
  { id: 17, name: 'The Star', nameRu: 'Звезда', arcana: 'major', meaning: 'Надежда, вдохновение, духовность', meaningReversed: 'Разочарование, потеря веры', imageUrl: '/assets/cards/17.jpg' },
  { id: 18, name: 'The Moon', nameRu: 'Луна', arcana: 'major', meaning: 'Иллюзии, интуиция, подсознание', meaningReversed: 'Прояснение, освобождение от страхов', imageUrl: '/assets/cards/18.jpg' },
  { id: 19, name: 'The Sun', nameRu: 'Солнце', arcana: 'major', meaning: 'Радость, успех, витальность', meaningReversed: 'Временные трудности, задержка успеха', imageUrl: '/assets/cards/19.jpg' },
  { id: 20, name: 'Judgement', nameRu: 'Суд', arcana: 'major', meaning: 'Возрождение, призвание, самоанализ', meaningReversed: 'Сомнения, самокритика, отказ от призвания', imageUrl: '/assets/cards/20.jpg' },
  { id: 21, name: 'The World', nameRu: 'Мир', arcana: 'major', meaning: 'Завершение, целостность, достижение', meaningReversed: 'Незавершённость, отсутствие закрытия', imageUrl: '/assets/cards/21.jpg' },
];

// Минорные арканы - Жезлы (14 карт)
export const WANDS: TarotCard[] = [
  { id: 22, name: 'Ace of Wands', nameRu: 'Туз Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Вдохновение, новые идеи, потенциал', meaningReversed: 'Задержка, отсутствие мотивации', imageUrl: '/assets/cards/22.jpg' },
  { id: 23, name: 'Two of Wands', nameRu: 'Двойка Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Планирование, принятие решений', meaningReversed: 'Страх перемен, плохое планирование', imageUrl: '/assets/cards/23.jpg' },
  { id: 24, name: 'Three of Wands', nameRu: 'Тройка Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Расширение, предвидение, прогресс', meaningReversed: 'Препятствия, задержки', imageUrl: '/assets/cards/24.jpg' },
  { id: 25, name: 'Four of Wands', nameRu: 'Четвёрка Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Праздник, гармония, домашний уют', meaningReversed: 'Конфликт в семье, нестабильность', imageUrl: '/assets/cards/25.jpg' },
  { id: 26, name: 'Five of Wands', nameRu: 'Пятёрка Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Конкуренция, конфликт, борьба', meaningReversed: 'Избегание конфликта, компромисс', imageUrl: '/assets/cards/26.jpg' },
  { id: 27, name: 'Six of Wands', nameRu: 'Шестёрка Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Победа, признание, успех', meaningReversed: 'Провал, отсутствие признания', imageUrl: '/assets/cards/27.jpg' },
  { id: 28, name: 'Seven of Wands', nameRu: 'Семёрка Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Защита, настойчивость, вызов', meaningReversed: 'Сдача позиций, усталость', imageUrl: '/assets/cards/28.jpg' },
  { id: 29, name: 'Eight of Wands', nameRu: 'Восьмёрка Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Быстрое движение, скорость, прогресс', meaningReversed: 'Задержки, разочарование', imageUrl: '/assets/cards/29.jpg' },
  { id: 30, name: 'Nine of Wands', nameRu: 'Девятка Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Стойкость, выносливость, последний рывок', meaningReversed: 'Паранойя, защитная позиция', imageUrl: '/assets/cards/30.jpg' },
  { id: 31, name: 'Ten of Wands', nameRu: 'Десятка Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Бремя, ответственность, тяжёлый труд', meaningReversed: 'Перегрузка, делегирование', imageUrl: '/assets/cards/31.jpg' },
  { id: 32, name: 'Page of Wands', nameRu: 'Паж Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Энтузиазм, исследование, открытия', meaningReversed: 'Поспешность, отсутствие направления', imageUrl: '/assets/cards/32.jpg' },
  { id: 33, name: 'Knight of Wands', nameRu: 'Рыцарь Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Энергия, страсть, приключение', meaningReversed: 'Импульсивность, безрассудство', imageUrl: '/assets/cards/33.jpg' },
  { id: 34, name: 'Queen of Wands', nameRu: 'Королева Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Уверенность, независимость, харизма', meaningReversed: 'Ревность, эгоизм', imageUrl: '/assets/cards/34.jpg' },
  { id: 35, name: 'King of Wands', nameRu: 'Король Жезлов', arcana: 'minor', suit: 'wands', meaning: 'Лидерство, видение, предпринимательство', meaningReversed: 'Деспотизм, импульсивность', imageUrl: '/assets/cards/35.jpg' },
];

// Минорные арканы - Кубки (14 карт)
export const CUPS: TarotCard[] = [
  { id: 36, name: 'Ace of Cups', nameRu: 'Туз Кубков', arcana: 'minor', suit: 'cups', meaning: 'Новая любовь, эмоции, интуиция', meaningReversed: 'Эмоциональная блокировка', imageUrl: '/assets/cards/36.jpg' },
  { id: 37, name: 'Two of Cups', nameRu: 'Двойка Кубков', arcana: 'minor', suit: 'cups', meaning: 'Партнёрство, любовь, гармония', meaningReversed: 'Дисбаланс в отношениях', imageUrl: '/assets/cards/37.jpg' },
  { id: 38, name: 'Three of Cups', nameRu: 'Тройка Кубков', arcana: 'minor', suit: 'cups', meaning: 'Дружба, праздник, сообщество', meaningReversed: 'Одиночество, изоляция', imageUrl: '/assets/cards/38.jpg' },
  { id: 39, name: 'Four of Cups', nameRu: 'Четвёрка Кубков', arcana: 'minor', suit: 'cups', meaning: 'Медитация, апатия, переоценка', meaningReversed: 'Новые возможности, мотивация', imageUrl: '/assets/cards/39.jpg' },
  { id: 40, name: 'Five of Cups', nameRu: 'Пятёрка Кубков', arcana: 'minor', suit: 'cups', meaning: 'Потеря, сожаление, печаль', meaningReversed: 'Принятие, движение вперёд', imageUrl: '/assets/cards/40.jpg' },
  { id: 41, name: 'Six of Cups', nameRu: 'Шестёрка Кубков', arcana: 'minor', suit: 'cups', meaning: 'Ностальгия, детство, воспоминания', meaningReversed: 'Застревание в прошлом', imageUrl: '/assets/cards/41.jpg' },
  { id: 42, name: 'Seven of Cups', nameRu: 'Семёрка Кубков', arcana: 'minor', suit: 'cups', meaning: 'Фантазии, выбор, иллюзии', meaningReversed: 'Ясность, определённость', imageUrl: '/assets/cards/42.jpg' },
  { id: 43, name: 'Eight of Cups', nameRu: 'Восьмёрка Кубков', arcana: 'minor', suit: 'cups', meaning: 'Уход, поиск смысла, разочарование', meaningReversed: 'Страх перемен, застой', imageUrl: '/assets/cards/43.jpg' },
  { id: 44, name: 'Nine of Cups', nameRu: 'Девятка Кубков', arcana: 'minor', suit: 'cups', meaning: 'Исполнение желаний, удовлетворение', meaningReversed: 'Неудовлетворённость, жадность', imageUrl: '/assets/cards/44.jpg' },
  { id: 45, name: 'Ten of Cups', nameRu: 'Десятка Кубков', arcana: 'minor', suit: 'cups', meaning: 'Семейное счастье, гармония, радость', meaningReversed: 'Семейные конфликты', imageUrl: '/assets/cards/45.jpg' },
  { id: 46, name: 'Page of Cups', nameRu: 'Паж Кубков', arcana: 'minor', suit: 'cups', meaning: 'Творчество, интуиция, мечты', meaningReversed: 'Эмоциональная незрелость', imageUrl: '/assets/cards/46.jpg' },
  { id: 47, name: 'Knight of Cups', nameRu: 'Рыцарь Кубков', arcana: 'minor', suit: 'cups', meaning: 'Романтика, очарование, воображение', meaningReversed: 'Нереалистичность, разочарование', imageUrl: '/assets/cards/47.jpg' },
  { id: 48, name: 'Queen of Cups', nameRu: 'Королева Кубков', arcana: 'minor', suit: 'cups', meaning: 'Эмпатия, интуиция, забота', meaningReversed: 'Эмоциональная нестабильность', imageUrl: '/assets/cards/48.jpg' },
  { id: 49, name: 'King of Cups', nameRu: 'Король Кубков', arcana: 'minor', suit: 'cups', meaning: 'Эмоциональный баланс, мудрость', meaningReversed: 'Эмоциональная манипуляция', imageUrl: '/assets/cards/49.jpg' },
];

// Минорные арканы - Мечи (14 карт)
export const SWORDS: TarotCard[] = [
  { id: 50, name: 'Ace of Swords', nameRu: 'Туз Мечей', arcana: 'minor', suit: 'swords', meaning: 'Ясность, истина, прорыв', meaningReversed: 'Путаница, хаос', imageUrl: '/assets/cards/50.jpg' },
  { id: 51, name: 'Two of Swords', nameRu: 'Двойка Мечей', arcana: 'minor', suit: 'swords', meaning: 'Тупик, сложный выбор', meaningReversed: 'Информационная перегрузка', imageUrl: '/assets/cards/51.jpg' },
  { id: 52, name: 'Three of Swords', nameRu: 'Тройка Мечей', arcana: 'minor', suit: 'swords', meaning: 'Горе, предательство, боль', meaningReversed: 'Исцеление, прощение', imageUrl: '/assets/cards/52.jpg' },
  { id: 53, name: 'Four of Swords', nameRu: 'Четвёрка Мечей', arcana: 'minor', suit: 'swords', meaning: 'Отдых, восстановление, созерцание', meaningReversed: 'Беспокойство, выгорание', imageUrl: '/assets/cards/53.jpg' },
  { id: 54, name: 'Five of Swords', nameRu: 'Пятёрка Мечей', arcana: 'minor', suit: 'swords', meaning: 'Конфликт, поражение, унижение', meaningReversed: 'Примирение, компромисс', imageUrl: '/assets/cards/54.jpg' },
  { id: 55, name: 'Six of Swords', nameRu: 'Шестёрка Мечей', arcana: 'minor', suit: 'swords', meaning: 'Переход, исцеление, путешествие', meaningReversed: 'Застой, сопротивление', imageUrl: '/assets/cards/55.jpg' },
  { id: 56, name: 'Seven of Swords', nameRu: 'Семёрка Мечей', arcana: 'minor', suit: 'swords', meaning: 'Хитрость, стратегия, обман', meaningReversed: 'Раскрытие обмана', imageUrl: '/assets/cards/56.jpg' },
  { id: 57, name: 'Eight of Swords', nameRu: 'Восьмёрка Мечей', arcana: 'minor', suit: 'swords', meaning: 'Ограничение, страх, беспомощность', meaningReversed: 'Освобождение, новые перспективы', imageUrl: '/assets/cards/57.jpg' },
  { id: 58, name: 'Nine of Swords', nameRu: 'Девятка Мечей', arcana: 'minor', suit: 'swords', meaning: 'Тревога, кошмары, страхи', meaningReversed: 'Надежда, преодоление страхов', imageUrl: '/assets/cards/58.jpg' },
  { id: 59, name: 'Ten of Swords', nameRu: 'Десятка Мечей', arcana: 'minor', suit: 'swords', meaning: 'Конец, крах, предательство', meaningReversed: 'Восстановление, новый рассвет', imageUrl: '/assets/cards/59.jpg' },
  { id: 60, name: 'Page of Swords', nameRu: 'Паж Мечей', arcana: 'minor', suit: 'swords', meaning: 'Любопытство, идеи, наблюдательность', meaningReversed: 'Сплетни, цинизм', imageUrl: '/assets/cards/60.jpg' },
  { id: 61, name: 'Knight of Swords', nameRu: 'Рыцарь Мечей', arcana: 'minor', suit: 'swords', meaning: 'Амбиции, решительность, скорость', meaningReversed: 'Безрассудство, агрессия', imageUrl: '/assets/cards/61.jpg' },
  { id: 62, name: 'Queen of Swords', nameRu: 'Королева Мечей', arcana: 'minor', suit: 'swords', meaning: 'Независимость, проницательность', meaningReversed: 'Жестокость, холодность', imageUrl: '/assets/cards/62.jpg' },
  { id: 63, name: 'King of Swords', nameRu: 'Король Мечей', arcana: 'minor', suit: 'swords', meaning: 'Интеллект, авторитет, истина', meaningReversed: 'Тирания, манипуляции', imageUrl: '/assets/cards/63.jpg' },
];

// Минорные арканы - Пентакли (14 карт)
export const PENTACLES: TarotCard[] = [
  { id: 64, name: 'Ace of Pentacles', nameRu: 'Туз Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Новые финансовые возможности', meaningReversed: 'Упущенные возможности', imageUrl: '/assets/cards/64.jpg' },
  { id: 65, name: 'Two of Pentacles', nameRu: 'Двойка Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Баланс, адаптация, приоритеты', meaningReversed: 'Дисбаланс, перегрузка', imageUrl: '/assets/cards/65.jpg' },
  { id: 66, name: 'Three of Pentacles', nameRu: 'Тройка Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Командная работа, мастерство', meaningReversed: 'Конфликты в команде', imageUrl: '/assets/cards/66.jpg' },
  { id: 67, name: 'Four of Pentacles', nameRu: 'Четвёрка Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Безопасность, контроль, экономия', meaningReversed: 'Жадность, страх потери', imageUrl: '/assets/cards/67.jpg' },
  { id: 68, name: 'Five of Pentacles', nameRu: 'Пятёрка Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Финансовые трудности, изоляция', meaningReversed: 'Восстановление, помощь', imageUrl: '/assets/cards/68.jpg' },
  { id: 69, name: 'Six of Pentacles', nameRu: 'Шестёрка Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Щедрость, благотворительность', meaningReversed: 'Долги, неравенство', imageUrl: '/assets/cards/69.jpg' },
  { id: 70, name: 'Seven of Pentacles', nameRu: 'Семёрка Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Терпение, инвестиции, рост', meaningReversed: 'Нетерпение, плохие вложения', imageUrl: '/assets/cards/70.jpg' },
  { id: 71, name: 'Eight of Pentacles', nameRu: 'Восьмёрка Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Мастерство, обучение, трудолюбие', meaningReversed: 'Перфекционизм, рутина', imageUrl: '/assets/cards/71.jpg' },
  { id: 72, name: 'Nine of Pentacles', nameRu: 'Девятка Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Изобилие, независимость, роскошь', meaningReversed: 'Финансовые проблемы', imageUrl: '/assets/cards/72.jpg' },
  { id: 73, name: 'Ten of Pentacles', nameRu: 'Десятка Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Богатство, наследие, семья', meaningReversed: 'Финансовые потери', imageUrl: '/assets/cards/73.jpg' },
  { id: 74, name: 'Page of Pentacles', nameRu: 'Паж Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Амбиции, планирование, обучение', meaningReversed: 'Недостаток прогресса', imageUrl: '/assets/cards/74.jpg' },
  { id: 75, name: 'Knight of Pentacles', nameRu: 'Рыцарь Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Надёжность, терпение, трудолюбие', meaningReversed: 'Скука, застой', imageUrl: '/assets/cards/75.jpg' },
  { id: 76, name: 'Queen of Pentacles', nameRu: 'Королева Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Практичность, забота, достаток', meaningReversed: 'Материализм, зависть', imageUrl: '/assets/cards/76.jpg' },
  { id: 77, name: 'King of Pentacles', nameRu: 'Король Пентаклей', arcana: 'minor', suit: 'pentacles', meaning: 'Богатство, бизнес, стабильность', meaningReversed: 'Жадность, расточительство', imageUrl: '/assets/cards/77.jpg' },
];

// Полная колода (78 карт)
export const FULL_DECK: TarotCard[] = [
  ...MAJOR_ARCANA,
  ...WANDS,
  ...CUPS,
  ...SWORDS,
  ...PENTACLES,
];

// Типы раскладов
export type ReadingType = 'classic' | 'situation' | 'relationship' | 'career' | 'custom' | 'random';

export const READING_TYPES: Record<ReadingType, { name: string; description: string; icon: string }> = {
  classic: { name: 'Классический', description: 'Универсальный расклад на любой вопрос', icon: '🔮' },
  situation: { name: 'На ситуацию', description: 'Анализ текущей ситуации и её развития', icon: '⭐' },
  relationship: { name: 'На отношения', description: 'Расклад о любви и партнёрстве', icon: '💕' },
  career: { name: 'На карьеру', description: 'Вопросы работы и финансов', icon: '💼' },
  custom: { name: 'Свои карты', description: 'Выберите карты сами', icon: '✨' },
  random: { name: 'Случайный', description: 'Карта дня без вопроса', icon: '🌙' },
};

// Генерация случайных карт
export function generateRandomCards(count: number = 3): TarotCard[] {
  const shuffled = [...FULL_DECK].sort(() => Math.random() - 0.5);
  const selected = shuffled.slice(0, count);
  return selected.map(card => ({
    ...card,
    isReversed: Math.random() < 0.3,
  }));
}

// Получить карту по ID
export function getCardById(id: number): TarotCard | undefined {
  return FULL_DECK.find(card => card.id === id);
}
