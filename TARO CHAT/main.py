"""
main.py
Основной файл запуска бота.
"""

import asyncio
import logging
import sys
import hashlib
from pathlib import Path
from datetime import datetime

from typing import Optional

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pytz import timezone
import sqlite3
from config import (
    BOT_TOKEN,
    LOG_PATH,
    TIMEZONE,
    DB_PATH,
    YOOMONEY_CHECK_INTERVAL,
    YOOMONEY_NOTIFICATION_SECRET,
    YOOMONEY_WEBHOOK_ENABLED,
    YOOMONEY_WEBHOOK_HOST,
    YOOMONEY_WEBHOOK_PORT,
    YOOMONEY_WEBHOOK_PATH,
    YOOMONEY_DRY_RUN,
)
from handlers import router
from admin_handlers import admin_router
from utils import add_free_requests_task, send_promotional_message
from yoomoney import yoomoney_payment
from database import db

# Глобальная переменная для бота (будет установлена в main)
bot_instance = None


def _calc_yoomoney_sha1(payload: dict, secret: str) -> str:
    s = (
        f"{payload.get('notification_type','')}&"
        f"{payload.get('operation_id','')}&"
        f"{payload.get('amount','')}&"
        f"{payload.get('currency','')}&"
        f"{payload.get('datetime','')}&"
        f"{payload.get('sender','')}&"
        f"{str(payload.get('codepro','')).lower()}&"
        f"{secret}&"
        f"{payload.get('label','')}"
    )
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


async def _yoomoney_webhook_handler(request: web.Request) -> web.Response:
    logger = logging.getLogger(__name__)

    if not YOOMONEY_NOTIFICATION_SECRET:
        logger.error("⚠️ YooMoney webhook enabled, but YOOMONEY_NOTIFICATION_SECRET is empty")
        return web.Response(status=500, text="secret_not_configured")

    try:
        data = dict(await request.post())
    except Exception as e:
        logger.error(f"⚠️ Failed to parse YooMoney webhook body: {e}")
        return web.Response(status=400, text="bad_request")

    got_hash = str(data.get("sha1_hash", "")).lower()
    expected_hash = _calc_yoomoney_sha1(data, YOOMONEY_NOTIFICATION_SECRET).lower()
    if not got_hash or got_hash != expected_hash:
        logger.warning(
            f"⚠️ YooMoney webhook sha1_hash mismatch: got={got_hash} expected={expected_hash} op_id={data.get('operation_id')}"
        )
        return web.Response(status=403, text="forbidden")

    label = str(data.get("label") or "")
    operation_id = str(data.get("operation_id") or "")

    if not label:
        logger.warning(f"⚠️ YooMoney webhook received without label (op_id={operation_id})")
        return web.Response(status=200, text="ok")

    if YOOMONEY_DRY_RUN:
        logger.info(
            f"🧪 YooMoney webhook DRY_RUN: would confirm payment by label={label} op_id={operation_id} amount={data.get('amount')} withdraw_amount={data.get('withdraw_amount')}"
        )
        return web.Response(status=200, text="ok")

    try:
        amount_received = round(float(data.get("amount", 0) or 0), 2)
    except (ValueError, TypeError):
        amount_received = 0.0

    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, user_id, amount, requests, status FROM payments WHERE yoomoney_label = ? ORDER BY timestamp DESC LIMIT 1",
                (label,),
            )
            row = cursor.fetchone()

        if not row:
            logger.info(f"🔔 YooMoney webhook: payment not found for label={label} (op_id={operation_id})")
            return web.Response(status=200, text="ok")

        payment = dict(row)
        payment_id = int(payment.get("id"))
        user_id = int(payment.get("user_id"))
        status = str(payment.get("status") or "")

        if status == "confirmed":
            return web.Response(status=200, text="ok")

        if operation_id:
            try:
                with sqlite3.connect(str(DB_PATH)) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id FROM payments WHERE yoomoney_operation_id = ? AND status = 'confirmed' LIMIT 1",
                        (operation_id,),
                    )
                    dup = cursor.fetchone()
                    if dup:
                        logger.warning(
                            f"⚠️ YooMoney webhook op_id already used: op_id={operation_id} payment={dup[0]} current_payment={payment_id}"
                        )
                        return web.Response(status=200, text="ok")
            except Exception as e:
                logger.warning(f"⚠️ YooMoney webhook cannot check operation_id uniqueness: {e}")

        success = await db.confirm_payment(payment_id=payment_id, status="confirmed")
        if not success:
            logger.error(f"❌ YooMoney webhook failed to confirm payment_id={payment_id} (label={label})")
            return web.Response(status=200, text="ok")

        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE payments SET yoomoney_operation_id = ?, amount_received = ? WHERE id = ?",
                    (operation_id or None, amount_received, payment_id),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"⚠️ YooMoney webhook could not store operation info for payment {payment_id}: {e}")

        if bot_instance:
            try:
                paid_amount = round(float(payment.get("amount", 0) or 0), 2)
            except (ValueError, TypeError):
                paid_amount = 0.0
            pending_requests = int(payment.get("requests", 0) or 0)

            try:
                await bot_instance.send_message(
                    user_id,
                    f"✅ <b>Платёж подтверждён!</b> 🌙\n\n"
                    f"💰 Сумма покупки: {paid_amount} руб.\n"
                    f"🔮 Добавлено премиум-запросов: {pending_requests}\n\n"
                    f"Спасибо за доверие! Карты ждут ваших вопросов. ✨",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"⚠️ YooMoney webhook failed to notify user {user_id}: {e}", exc_info=True)

        logger.info(f"✅ YooMoney webhook confirmed payment_id={payment_id} label={label} op_id={operation_id}")
        return web.Response(status=200, text="ok")
    except Exception as e:
        logger.error(f"⚠️ YooMoney webhook handler error: {e}", exc_info=True)
        return web.Response(status=200, text="ok")

def setup_logging() -> None:
    """
    Настройка логирования для production.
    """
    log_path = Path(LOG_PATH)
    log_dir = log_path.parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Файловый обработчик
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Отключаем лишние логи для production
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('aiogram.event').setLevel(logging.WARNING)  # Убираем спам "Update id=... handled"
    logging.getLogger('aiohttp.server').setLevel(logging.ERROR)  # Игнорируем ошибки от сканеров (400 BadStatusLine)
    
    # Устанавливаем INFO для yoomoney
    logging.getLogger('yoomoney').setLevel(logging.INFO)
    
    logging.info("🔮 Logging setup completed")
    logging.info("✅ Production mode: INFO logs, minimal spam, webhook disabled by default")

async def cleanup_old_pending_task() -> None:
    """
    Очищает старые pending платежи (раз в день).
    Удаляет записи в статусе 'pending' старше 7 дней.
    """
    logger = logging.getLogger(__name__)
    try:
        deleted_count = await db.cleanup_old_pending(days=7)
        if deleted_count > 0:
            logger.info(f"🧹 Cleaned up {deleted_count} old pending payments")
    except Exception as e:
        logger.error(f"⚠️ Error in cleanup_old_pending_task: {e}", exc_info=True)

async def check_yoomoney_payments() -> None:
    """
    Проверяет платежи через YooMoney и начисляет запросы.
    Запускается каждые 45 секунд через scheduler.
    
    Подтверждает платежи только по точному совпадению label.
    """
    logger = logging.getLogger(__name__)
    amount_eps = 0.02

    def amount_close(a: float, b: float) -> bool:
        return abs(a - b) <= amount_eps
    
    try:
        # Получаем ожидающие платежи из базы данных
        pending_payments = await db.get_pending_payments()
        
        if not pending_payments:
            logger.debug("No pending payments in database")
            return
        
        logger.info(f"🔮 Found {len(pending_payments)} pending payments to check")
        
        # Получаем операции из YooMoney API (расширяем до 72 часов для задержек API)
        operations = await yoomoney_payment.get_recent_operations(hours=72)
        
        if not operations:
            logger.debug("No recent operations from YooMoney API")
            return
        
        logger.info(f"🔮 Found {len(operations)} recent operations from YooMoney API")
        
        pending_labels = {
            p.get("yoomoney_label") for p in pending_payments if p.get("yoomoney_label")
        }

        pending_amounts = set()
        for p in pending_payments:
            try:
                gross_amount = round(float(p.get("amount", 0) or 0), 2)
                pending_amounts.add(gross_amount)
                pending_amounts.add(round(gross_amount * 0.97, 2))
                pending_amounts.add(round(gross_amount / 1.01, 2))
            except (ValueError, TypeError):
                continue

        operations_by_label = {}
        incoming_success_ops = []
        operation_details_cache: dict[str, str] = {}
        operation_details_calls = 0
        max_operation_details_calls = 20
        for operation in operations:
            op_direction = operation.get("direction", "")
            op_status = operation.get("status", "")
            op_type = operation.get("type", "")
            op_id = operation.get("operation_id")

            if op_direction != "in" or op_status != "success" or op_type not in ["deposition", "incoming-transfer"]:
                continue

            incoming_success_ops.append(operation)

            op_label = operation.get("label")
            if not op_label:
                details = operation.get("details")
                if isinstance(details, dict):
                    op_label = details.get("label")

            if not op_label and op_id and pending_labels and op_id not in operation_details_cache:
                try:
                    op_amount = round(float(operation.get("amount", 0) or 0), 2)
                except (ValueError, TypeError):
                    op_amount = None

                if op_amount is not None and any(amount_close(op_amount, v) for v in pending_amounts):
                    if operation_details_calls < max_operation_details_calls:
                        try:
                            details_data = await yoomoney_payment.get_operation_details(str(op_id))
                            operation_details_calls += 1
                            if isinstance(details_data, dict):
                                fetched_label = details_data.get("label")
                                if fetched_label:
                                    operation_details_cache[str(op_id)] = fetched_label
                                    op_label = fetched_label
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to load operation-details for {op_id}: {e}")

            # Без label платеж нельзя безопасно сопоставить
            if not op_label:
                continue

            # Если есть несколько операций с одинаковым label — берём последнюю по времени/порядку (перезапишем)
            operations_by_label[op_label] = operation

        logger.info(
            f"🔮 Found {len(operations_by_label)} valid incoming operations with label "
            f"(direction=in, status=success)"
        )

        # Сопоставляем ожидающие платежи с операциями только по label
        for pending in pending_payments:
            pending_user_id = pending.get("user_id")
            pending_id = pending.get("id")
            pending_label = pending.get("yoomoney_label", "")
            pending_timestamp = pending.get("timestamp", "")
            matched_by_fallback = False

            if not pending_user_id:
                logger.warning(f"⚠️ Invalid pending payment {pending_id}: user_id={pending_user_id}")
                continue

            if not pending_label:
                logger.warning(f"⚠️ Pending payment {pending_id} has no yoomoney_label, skipping")
                continue

            logger.info(
                f"🔍 Checking pending payment {pending_id}: user={pending_user_id}, "
                f"label={pending_label}, created={pending_timestamp}"
            )
            
            # Парсим время создания платежа
            try:
                if pending_timestamp:
                    # Формат timestamp в SQLite: 'YYYY-MM-DD HH:MM:SS'
                    payment_created = datetime.strptime(pending_timestamp, "%Y-%m-%d %H:%M:%S")
                    try:
                        local_tz = timezone(TIMEZONE)
                        payment_created = (
                            local_tz.localize(payment_created)
                            .astimezone(timezone("UTC"))
                            .replace(tzinfo=None)
                        )
                    except Exception:
                        pass
                else:
                    # Если timestamp нет, пропускаем проверку времени (старые записи)
                    payment_created = None
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Could not parse payment timestamp {pending_timestamp}: {e}")
                payment_created = None
            
            matched_operation = operations_by_label.get(pending_label)

            if not matched_operation:
                pending_amount_raw = pending.get("amount", 0)
                try:
                    pending_amount = float(pending_amount_raw)
                except (ValueError, TypeError):
                    pending_amount = 0.0

                pending_expected_received_ac = round(pending_amount * 0.97, 2)
                pending_expected_received_pc = round(pending_amount / 1.01, 2)
                expected_received_candidates = {
                    round(pending_amount, 2),
                    pending_expected_received_ac,
                    pending_expected_received_pc,
                }

                candidates = []
                for op in incoming_success_ops:
                    try:
                        op_amount = round(float(op.get("amount", 0) or 0), 2)
                    except (ValueError, TypeError):
                        continue

                    if not any(amount_close(op_amount, v) for v in expected_received_candidates):
                        continue

                    if payment_created and op.get("datetime"):
                        try:
                            op_datetime_clean = str(op.get("datetime")).replace('Z', '').split('.')[0]
                            op_dt = datetime.strptime(op_datetime_clean, "%Y-%m-%dT%H:%M:%S")
                            time_diff = (op_dt - payment_created).total_seconds()
                            if time_diff < -300:
                                continue
                        except Exception:
                            pass

                    candidates.append(op)

                resolved_by_details = None
                if candidates:
                    for op in candidates:
                        op_id = op.get("operation_id")
                        if not op_id:
                            continue

                        op_label = op.get("label")
                        if not op_label:
                            details = op.get("details")
                            if isinstance(details, dict):
                                op_label = details.get("label")

                        if not op_label:
                            op_label = operation_details_cache.get(str(op_id))

                        if not op_label and operation_details_calls < max_operation_details_calls:
                            try:
                                details_data = await yoomoney_payment.get_operation_details(str(op_id))
                                operation_details_calls += 1
                                if isinstance(details_data, dict):
                                    fetched_label = details_data.get("label")
                                    if fetched_label:
                                        operation_details_cache[str(op_id)] = fetched_label
                                        op_label = fetched_label
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to load operation-details for candidate {op_id}: {e}")

                        if op_label and op_label == pending_label:
                            resolved_by_details = op
                            break

                if resolved_by_details is not None:
                    matched_operation = resolved_by_details
                    matched_by_fallback = True
                    logger.info(
                        f"✅ Found payment {pending_id} by operation-details label match (fallback candidates={len(candidates)})"
                    )

                if resolved_by_details is None:
                    if len(candidates) == 1:
                        only_candidate = candidates[0]
                        candidate_id = only_candidate.get("operation_id")

                        candidate_label = only_candidate.get("label")
                        if not candidate_label:
                            details = only_candidate.get("details")
                            if isinstance(details, dict):
                                candidate_label = details.get("label")

                        if not candidate_label and candidate_id:
                            candidate_label = operation_details_cache.get(str(candidate_id))

                        if not candidate_label and candidate_id and operation_details_calls < max_operation_details_calls:
                            try:
                                details_data = await yoomoney_payment.get_operation_details(str(candidate_id))
                                operation_details_calls += 1
                                if isinstance(details_data, dict):
                                    fetched_label = details_data.get("label")
                                    if fetched_label:
                                        operation_details_cache[str(candidate_id)] = fetched_label
                                        candidate_label = fetched_label
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to load operation-details for fallback candidate {candidate_id}: {e}")

                        if candidate_label and candidate_label != pending_label:
                            logger.warning(
                                f"⚠️ Single amount-matched operation {candidate_id} has different label, skipping payment {pending_id}"
                            )
                            continue

                        matched_operation = only_candidate
                        matched_by_fallback = True
                        logger.info(
                            f"✅ Found payment {pending_id} by amount fallback: expected={pending_amount:.2f} / received≈{pending_expected_received_ac:.2f} or {pending_expected_received_pc:.2f}"
                        )
                    elif len(candidates) == 0:
                        logger.info(
                            f"⏳ No matching operation found for payment {pending_id} (label={pending_label}, expected={pending_amount:.2f} / received≈{pending_expected_received_ac:.2f} or {pending_expected_received_pc:.2f})"
                        )
                        continue
                    else:
                        logger.warning(
                            f"⚠️ Ambiguous operations for payment {pending_id} (expected={pending_amount:.2f} / received≈{pending_expected_received_ac:.2f} or {pending_expected_received_pc:.2f}): {len(candidates)} candidates"
                        )
                        for op in candidates[:5]:
                            logger.warning(
                                f"    candidate op_id={op.get('operation_id')}, amount={op.get('amount')}, datetime={op.get('datetime')}"
                            )
                        continue

            operation_amount = float(matched_operation.get("amount", 0))
            operation_id = matched_operation.get("operation_id", "unknown")
            op_datetime_str = matched_operation.get("datetime", "")

            if operation_id and operation_id != "unknown":
                try:
                    with sqlite3.connect(str(DB_PATH)) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT id FROM payments WHERE yoomoney_operation_id = ? AND status = 'confirmed' LIMIT 1",
                            (operation_id,)
                        )
                        dup = cursor.fetchone()
                        if dup:
                            logger.warning(
                                f"⚠️ Operation {operation_id} already used by payment {dup[0]}, skipping payment {pending_id}"
                            )
                            continue
                except Exception as e:
                    logger.warning(f"⚠️ Could not check operation_id uniqueness: {e}")

            # Доп.проверка времени: не подтверждаем по явно старой операции
            if payment_created and op_datetime_str:
                try:
                    op_datetime_clean = op_datetime_str.replace('Z', '').split('.')[0]
                    op_datetime = datetime.strptime(op_datetime_clean, "%Y-%m-%dT%H:%M:%S")
                    time_diff = (op_datetime - payment_created).total_seconds()
                    if time_diff < -300:
                        logger.warning(
                            f"⚠️ Skipping operation {operation_id}: created {op_datetime} is BEFORE payment {pending_id} "
                            f"created {payment_created} (diff: {time_diff:.0f}s)"
                        )
                        continue
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ Could not parse operation datetime '{op_datetime_str}': {e}")

            if matched_by_fallback:
                logger.info(f"✅ Found payment {pending_id} by fallback (no label match)")
            else:
                logger.info(f"✅ Found payment {pending_id} by label match: {pending_label}")
            logger.info(f"   Operation ID: {operation_id}, Amount: {operation_amount}")
            
            # Проверяем, не обработан ли уже этот платёж
            with sqlite3.connect(str(DB_PATH)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT status FROM payments WHERE id = ?",
                    (pending_id,)
                )
                result = cursor.fetchone()
                
                if result and result[0] == "confirmed":
                    logger.info(f"🔮 Payment {pending_id} already processed")
                    continue
            
            # Подтверждаем платёж и начисляем запросы строго из записи payments
            pending_requests = int(pending.get("requests", 0) or 0)
            try:
                pending_paid_amount = round(float(pending.get("amount", 0) or 0), 2)
            except (ValueError, TypeError):
                pending_paid_amount = 0.0

            if YOOMONEY_DRY_RUN:
                logger.info(
                    f"🧪 DRY_RUN: would confirm payment {pending_id} for user {pending_user_id} "
                    f"(purchase_amount={pending_paid_amount}, amount_received={operation_amount}, requests={pending_requests}, op_id={operation_id})"
                )
                continue

            logger.info(f"💰 Confirming payment {pending_id} and crediting {pending_requests} requests to user {pending_user_id}...")
            success = await db.confirm_payment(payment_id=pending_id, status="confirmed")

            if success:
                # Пишем в платеж operation_id/amount_received, если в таблице есть колонки
                try:
                    with sqlite3.connect(str(DB_PATH)) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE payments SET yoomoney_operation_id = ?, amount_received = ? WHERE id = ?",
                            (operation_id, operation_amount, pending_id)
                        )
                        conn.commit()
                except Exception as e:
                    logger.warning(f"⚠️ Could not store operation info for payment {pending_id}: {e}")

                # Извлекаем package_key из label для логов
                package_key = yoomoney_payment._extract_package_key_from_label(pending_label) or "unknown"
                
                logger.info(
                    f"✅ Payment {pending_id} confirmed and requests credited to user {pending_user_id} "
                    f"(package: {package_key}, amount_received: {operation_amount}, requests: {pending_requests})"
                )
                
                # Уведомляем пользователя
                if bot_instance:
                    try:
                        await bot_instance.send_message(
                            pending_user_id,
                            f"✅ <b>Платёж подтверждён!</b> 🌙\n\n"
                            f"💰 Сумма покупки: {pending_paid_amount} руб.\n"
                            f"🔮 Добавлено премиум-запросов: {pending_requests}\n\n"
                            f"🎁 <b>Бонус за покупку:</b> Напишите в поддержку @katya_katerina_bu и получите секретный расклад в подарок! ✨\n\n"
                            f"Спасибо за доверие! Карты ждут ваших вопросов. ✨",
                            parse_mode='HTML'
                        )
                        logger.info(f"✅ Notification sent to user {pending_user_id}")
                    except Exception as e:
                        logger.error(f"⚠️ Failed to notify user {pending_user_id}: {e}", exc_info=True)
            else:
                logger.error(f"❌ Failed to credit requests to user {pending_user_id} for payment {pending_id}")
                
    except Exception as e:
        logger.error(f"⚠️ Error in check_yoomoney_payments: {e}", exc_info=True)

async def main() -> None:
    """
    Основная функция запуска бота.
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    global bot_instance
    webhook_runner: Optional[web.AppRunner] = None
    
    try:
        # Инициализируем базу данных
        db.init_db()
        logger.info("🔮 Database initialized")
        
        # Создаем бота
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode='HTML')
        )
        bot_instance = bot  # Сохраняем для использования в scheduled tasks
        
        # Создаем диспетчер
        dp = Dispatcher(storage=MemoryStorage())
        
        # Регистрируем роутеры
        dp.include_router(router)
        dp.include_router(admin_router)
        
        # Настраиваем планировщик задач
        scheduler = AsyncIOScheduler(timezone=timezone(TIMEZONE))
        
        # Задача на добавление бесплатных запросов каждые 24 часа
        scheduler.add_job(
            add_free_requests_task,
            trigger='interval',
            hours=24,
            kwargs={'bot': bot},
            id='add_free_requests',
            replace_existing=True
        )

        # Рекламная рассылка каждые 12 часов
        scheduler.add_job(
            send_promotional_message,
            trigger='interval',
            hours=12,
            kwargs={'bot': bot},
            id='send_promotion',
            replace_existing=True
        )
        
        # Задача на проверку платежей YooMoney каждые 45 секунд
        scheduler.add_job(
            check_yoomoney_payments,
            trigger='interval',
            seconds=YOOMONEY_CHECK_INTERVAL,
            id='check_yoomoney_payments',
            replace_existing=True
        )
        
        # Задача на очистку старых pending платежей (раз в день)
        scheduler.add_job(
            cleanup_old_pending_task,
            trigger='cron',
            hour=3,  # Выполнять в 3:00 утра
            minute=0,
            id='cleanup_old_pending',
            replace_existing=True
        )
        
        # Запускаем планировщик
        scheduler.start()
        logger.info("⏰ Scheduler started with YooMoney payment checking")

        if YOOMONEY_WEBHOOK_ENABLED:
            try:
                app = web.Application()
                app.router.add_post(YOOMONEY_WEBHOOK_PATH, _yoomoney_webhook_handler)
                webhook_runner = web.AppRunner(app)
                await webhook_runner.setup()
                site = web.TCPSite(webhook_runner, host=YOOMONEY_WEBHOOK_HOST, port=YOOMONEY_WEBHOOK_PORT)
                await site.start()
                logger.info(
                    f"🔔 YooMoney webhook server started: http://{YOOMONEY_WEBHOOK_HOST}:{YOOMONEY_WEBHOOK_PORT}{YOOMONEY_WEBHOOK_PATH}"
                )
            except Exception as e:
                logger.error(f"⚠️ Failed to start YooMoney webhook server: {e}", exc_info=True)

        # Запускаем бота
        logger.info("🔮 Starting bot...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.exception(f"⚠️ Bot crashed: {e}")
    finally:
        if webhook_runner:
            try:
                await webhook_runner.cleanup()
            except Exception:
                pass
        logger.info("✨ Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
