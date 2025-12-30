"""
yoomoney.py
Модуль для автоматической работы с API ЮMoney (YooMoney).
Генерация ссылок на оплату и автоматическая проверка платежей.
"""

import logging
import asyncio
import httpx
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode

from config import (
    YOOMONEY_WALLET,
    YOOMONEY_BOT_TOKEN,
    YOOMONEY_LABEL_PREFIX,
    YOOMONEY_LOG_PATH,
    PAYMENT_OPTIONS,
    YOOMONEY_CLIENT_ID,
    YOOMONEY_CLIENT_SECRET,
    YOOMONEY_REDIRECT_URI,
    YOOMONEY_OAUTH_AUTH_URL,
    YOOMONEY_OAUTH_TOKEN_URL,
    YOOMONEY_SCOPE
)

# Настройка отдельного логгера для YooMoney
yoomoney_logger = logging.getLogger("yoomoney")
yoomoney_logger.setLevel(logging.INFO)  # Было DEBUG, теперь INFO для production

# Создаём файловый обработчик для yoomoney.log
yoomoney_log_path = YOOMONEY_LOG_PATH
yoomoney_log_path.parent.mkdir(parents=True, exist_ok=True)

file_handler = logging.FileHandler(yoomoney_log_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)  # Было DEBUG
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
yoomoney_logger.addHandler(file_handler)

# Также добавляем консольный обработчик
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
yoomoney_logger.addHandler(console_handler)


class YooMoneyPayment:
    """Класс для работы с платежами через ЮMoney."""
    
    API_BASE_URL = "https://yoomoney.ru/api"
    OAUTH_AUTH_URL = YOOMONEY_OAUTH_AUTH_URL
    OAUTH_TOKEN_URL = YOOMONEY_OAUTH_TOKEN_URL
    
    def __init__(self):
        self.wallet = YOOMONEY_WALLET
        self.token = YOOMONEY_BOT_TOKEN
        self.label_prefix = YOOMONEY_LABEL_PREFIX
        self.client_id = YOOMONEY_CLIENT_ID
        self.client_secret = YOOMONEY_CLIENT_SECRET
        self.redirect_uri = YOOMONEY_REDIRECT_URI
        self.scope = YOOMONEY_SCOPE

    def _build_quickpay_link(self, amount: float, label: str) -> str:
        params = {
            "writer": "seller",
            "targets": "Tarot",
            "default-sum": f"{amount:.2f}",
            "button-text": "11",
            "payment-type-choice": "on",
            "mobile-payment-type-choice": "on",
            "comment": "off",
            "hint": "",
            "successURL": "",
            "quickpay": "shop",
            "account": self.wallet,
            "label": label,
        }
        return f"https://yoomoney.ru/quickpay/shop-widget?{urlencode(params)}"

    def generate_label(self, user_id: int, package_key: str) -> str:
        import time
        import random
        timestamp = int(time.time() * 1000)
        random_suffix = random.randint(1000, 9999)
        return f"{self.label_prefix}user_{user_id}_pkg_{package_key}_{timestamp}_{random_suffix}"

    def build_payment_url(self, amount: float, label: str) -> str:
        return self._build_quickpay_link(amount=amount, label=label)
    
    def get_authorization_url(self, instance_name: Optional[str] = None) -> str:
        """
        Генерирует URL для авторизации через OAuth.
        
        Args:
            instance_name: Опциональный идентификатор инстанса авторизации
            
        Returns:
            URL для авторизации
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": self.scope
        }
        
        if instance_name:
            params["instance_name"] = instance_name
        
        query_string = urlencode(params)
        auth_url = f"{self.OAUTH_AUTH_URL}?{query_string}"
        
        yoomoney_logger.info(f"Generated authorization URL: {auth_url}")
        return auth_url
    
    async def exchange_code_for_token(self, code: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Обменивает временный код авторизации на постоянный токен.
        
        Args:
            code: Временный код авторизации из redirect_uri
            
        Returns:
            Кортеж (access_token, error_message)
            access_token - токен или None в случае ошибки
            error_message - описание ошибки или None при успехе
        """
        try:
            url = self.OAUTH_TOKEN_URL
            
            form_data = {
                "code": code,
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri
            }
            
            # Добавляем client_secret, если он указан
            if self.client_secret:
                form_data["client_secret"] = self.client_secret
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            yoomoney_logger.info(f"Exchanging authorization code for token...")
            yoomoney_logger.info(f"Client ID: {self.client_id[:20]}...")
            yoomoney_logger.info(f"Redirect URI: {self.redirect_uri}")
            yoomoney_logger.info(f"Code length: {len(code)}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, data=form_data, headers=headers)
                
                response_text = response.text
                yoomoney_logger.info(f"Response status: {response.status_code}")
                yoomoney_logger.info(f"Response body: {response_text[:500]}")
                
                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}: {response_text}"
                    yoomoney_logger.error(f"Failed to exchange code for token: {error_msg}")
                    return None, error_msg
                
                try:
                    data = response.json()
                except Exception as e:
                    error_msg = f"Invalid JSON response: {response_text[:200]}"
                    yoomoney_logger.error(error_msg)
                    return None, error_msg
                
                if "error" in data:
                    error = data.get("error", "unknown")
                    error_desc = data.get("error_description", "")
                    
                    # Детальные сообщения об ошибках
                    error_messages = {
                        "invalid_request": "Неверный запрос. Проверьте параметры.",
                        "unauthorized": "Неверный client_id или client_secret.",
                        "invalid_grant": "Код истёк, уже использован или неверный. Получите новый код.",
                        "invalid_client": "Неверный client_id или client_secret.",
                    }
                    
                    detailed_error = error_messages.get(error, error_desc or error)
                    full_error = f"{error}: {detailed_error}"
                    
                    yoomoney_logger.error(f"OAuth error: {full_error}")
                    return None, full_error
                
                if "access_token" in data:
                    access_token = data["access_token"]
                    if access_token and len(access_token) > 10:  # Проверяем, что токен не пустой
                        yoomoney_logger.info("✅ Successfully obtained access token")
                        return access_token, None
                    else:
                        error_msg = "Получен пустой токен. Возможно, код истёк или неверные настройки."
                        yoomoney_logger.error(error_msg)
                        yoomoney_logger.error(f"Response data: {data}")
                        return None, error_msg
                else:
                    error_msg = f"No access_token in response: {data}"
                    yoomoney_logger.error(error_msg)
                    return None, error_msg
                    
        except httpx.TimeoutException:
            error_msg = "Timeout при обмене кода на токен. Попробуйте позже."
            yoomoney_logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Ошибка при обмене кода: {str(e)}"
            yoomoney_logger.error(f"Error exchanging code for token: {e}", exc_info=True)
            return None, error_msg
    
    async def revoke_token(self, token: Optional[str] = None) -> bool:
        """
        Отзывает (аннулирует) токен авторизации.
        
        Args:
            token: Токен для отзыва (если None, используется self.token)
            
        Returns:
            True если успешно, False в случае ошибки
        """
        token_to_revoke = token or self.token
        
        if not token_to_revoke:
            yoomoney_logger.warning("No token to revoke")
            return False
        
        try:
            url = f"{self.API_BASE_URL}/revoke"
            
            headers = {
                "Authorization": f"Bearer {token_to_revoke}"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                
                if response.status_code == 200:
                    yoomoney_logger.info("✅ Token revoked successfully")
                    return True
                else:
                    yoomoney_logger.error(
                        f"Failed to revoke token: {response.status_code} - {response.text}"
                    )
                    return False
                    
        except Exception as e:
            yoomoney_logger.error(f"Error revoking token: {e}", exc_info=True)
            return False
    
    async def generate_payment_link(
        self, 
        user_id: int, 
        amount: float,
        requests_count: int,
        package_key: str
    ) -> Tuple[str, str]:
        """
        Генерирует ссылку на оплату через ЮMoney и создаёт pending платёж в БД.
        
        Args:
            user_id: ID пользователя в Telegram
            amount: Сумма платежа
            requests_count: Количество запросов в пакете
            package_key: Ключ пакета (buy_1, buy_2, buy_3, test_5)
            
        Returns:
            Кортеж (payment_url, label)
        """
        from database import db
        
        # Генерируем уникальный label
        label = self.generate_label(user_id=user_id, package_key=package_key)
        
        # Добавляем небольшую случайную сумму для уникальности платежа
        import random
        random_kopecks = random.randint(0, 99) / 100
        final_amount = round(amount + random_kopecks, 2)
        
        yoomoney_logger.info(
            f"💳 Generating payment link: user={user_id}, package={package_key}, "
            f"amount={amount} -> {final_amount}, requests={requests_count}, label={label}"
        )
        
        # Создаём pending платёж в БД
        try:
            payment_id = await db.create_pending_payment(
                user_id=user_id,
                amount=final_amount,
                requests=requests_count,
                yoomoney_label=label
            )
            
            if payment_id:
                yoomoney_logger.info(
                    f"✅ Created pending payment ID={payment_id} for user {user_id}: "
                    f"label={label}, amount={final_amount}, requests={requests_count}"
                )
            else:
                yoomoney_logger.warning(
                    f"⚠️ Failed to create pending payment for user {user_id} (returned None), but continuing..."
                )
        except Exception as e:
            yoomoney_logger.error(f"⚠️ Error creating pending payment: {e}", exc_info=True)
        
        # Генерируем ссылку на оплату
        payment_url = self.build_payment_url(amount=final_amount, label=label)
        
        yoomoney_logger.info(
            f"🔗 Payment link ready for user {user_id}: label={label[:50]}..."
        )
        
        return payment_url, label
    
    async def get_recent_operations(self, hours: int = 24) -> list[Dict[str, Any]]:
        """
        Получает недавние операции из YooMoney API.
        
        Args:
            hours: Количество часов назад для фильтрации операций
            
        Returns:
            Список операций
        """
        if not self.token:
            yoomoney_logger.warning("YooMoney token not set, skipping operation check")
            return []
        
        try:
            url = f"{self.API_BASE_URL}/operation-history"

            # Не используем from/till в запросе, чтобы не зависеть от часового пояса сервера.
            # Берём последние операции (records=100) и фильтруем по времени локально.
            form_data = {
                "records": "100",
                "details": "true",
            }
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            yoomoney_logger.debug(f"Getting recent operations (last {hours} hours)")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, data=form_data, headers=headers)
                
                if response.status_code != 200:
                    yoomoney_logger.error(f"Failed to get recent operations: {response.status_code}")
                    return []
                
                try:
                    data = response.json()
                except Exception as e:
                    yoomoney_logger.error(f"Failed to parse JSON response: {e}")
                    return []
                
                if "error" in data:
                    yoomoney_logger.error(f"YooMoney API error: {data.get('error')}")
                    return []
                
                if "operations" not in data:
                    return []
                
                operations = data.get("operations", [])

                if hours and hours > 0:
                    cutoff = datetime.utcnow() - timedelta(hours=hours)
                    filtered: list[Dict[str, Any]] = []
                    for op in operations:
                        dt_raw = op.get("datetime")
                        if not dt_raw:
                            # Если datetime отсутствует — НЕ отбрасываем операцию, чтобы не потерять платёж
                            filtered.append(op)
                            continue
                        try:
                            dt_clean = str(dt_raw).replace('Z', '').split('.')[0]
                            op_dt = datetime.strptime(dt_clean, "%Y-%m-%dT%H:%M:%S")
                        except Exception:
                            # Если не смогли распарсить — не отбрасываем, чтобы не потерять платёж
                            filtered.append(op)
                            continue
                        if op_dt >= cutoff:
                            filtered.append(op)
                    operations = filtered

                yoomoney_logger.info(f"Received {len(operations)} recent operations (last {hours} hours)")
                return operations
                
        except Exception as e:
            yoomoney_logger.error(f"Error getting recent operations: {e}", exc_info=True)
            return []
    
    async def check_payments(self) -> list[Dict[str, Any]]:
        """
        Проверяет историю операций на наличие новых платежей.
        Использует POST запрос с form data согласно документации YooMoney API.
        
        Returns:
            Список найденных платежей с метками tarot_luna_*
        """
        if not self.token:
            yoomoney_logger.warning("YooMoney token not set, skipping payment check")
            return []
        
        try:
            url = f"{self.API_BASE_URL}/operation-history"
            
            # Формируем form data согласно документации YooMoney
            # Согласно документации: type может быть "deposition" (пополнение) или "payment" (платежи)
            # Можно указать несколько типов через пробел
            # Для входящих платежей нужны: deposition (зачисление) и incoming-transfer (входящий перевод)
            # Но incoming-transfer не является значением параметра type в запросе!
            # Параметр type в запросе: "deposition" или "payment"
            # Тип операции в ответе: "deposition", "incoming-transfer", "payment-shop", "outgoing-transfer"
            # Поэтому запрашиваем все операции (без type) и фильтруем по direction="in"
            form_data = {
                # Не указываем type, чтобы получить все операции, затем фильтруем по direction="in"
                # Это гарантирует, что мы получим и deposition, и incoming-transfer
                "records": "100",  # Максимум записей согласно документации (1-100)
                "details": "true"  # Получаем детальную информацию (требует права operation-details)
            }
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            yoomoney_logger.info(f"Checking YooMoney payments via POST to {url}")
            yoomoney_logger.debug(f"Request form_data: type={form_data.get('type')}, records={form_data.get('records')}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Используем POST с form data
                response = await client.post(url, data=form_data, headers=headers)
                
                yoomoney_logger.debug(f"Response status: {response.status_code}")
                
                if response.status_code != 200:
                    error_text = response.text[:500] if len(response.text) > 500 else response.text
                    yoomoney_logger.error(f"Failed to get operation history: {response.status_code} - {error_text}")
                    return []
                
                try:
                    data = response.json()
                except Exception as e:
                    yoomoney_logger.error(f"Failed to parse JSON response: {e}, response text: {response.text[:500]}")
                    return []
                
                yoomoney_logger.debug(f"Response keys: {list(data.keys())}")
                
                # Проверяем наличие ошибки
                if "error" in data:
                    yoomoney_logger.error(f"YooMoney API error: {data['error']}")
                    if "error_description" in data:
                        yoomoney_logger.error(f"Error description: {data['error_description']}")
                    return []
                
                if "operations" not in data:
                    yoomoney_logger.warning("No 'operations' field in response")
                    yoomoney_logger.debug(f"Response data keys: {list(data.keys())}")
                    if "next_record" in data:
                        yoomoney_logger.debug(f"next_record: {data.get('next_record')}")
                    return []
                
                operations = data.get("operations", [])
                yoomoney_logger.info(f"Received {len(operations)} operations from YooMoney API")
                
                if "next_record" in data:
                    yoomoney_logger.debug(f"Has next_record: {data.get('next_record')} (more pages available)")
                
                if len(operations) == 0:
                    yoomoney_logger.info("No operations found in response (this is normal if no recent payments)")
                    return []
                
                # ====== ПОЛНЫЙ DEBUG ВСЕ LABELS/AMOUNTS/DATETIME ДО ФИЛЬТРАЦИИ ======
                yoomoney_logger.info(f"🔍 API returned {len(operations)} operations TOTAL")
                yoomoney_logger.info("🔍 ALL LABELS from API:")
                for i, op in enumerate(operations):
                    label = op.get('label', 'None')
                    yoomoney_logger.info(f"   [{i+1}] {label}")
                
                yoomoney_logger.info("🔍 ALL AMOUNTS from API:")
                for i, op in enumerate(operations):
                    amount = op.get('amount', 0)
                    yoomoney_logger.info(f"   [{i+1}] {amount}")
                
                yoomoney_logger.info("🔍 ALL DATETIMES from API:")
                for i, op in enumerate(operations):
                    dt = op.get('datetime', 'None')
                    yoomoney_logger.info(f"   [{i+1}] {dt}")
                # ====== КОНЕЦ DEBUG ======
                
                # Логируем ВСЕ операции для отладки
                yoomoney_logger.info(f"=== Analyzing {len(operations)} operations ===")
                for i, op in enumerate(operations):
                    op_id = op.get('operation_id', 'unknown')
                    op_type = op.get('type', 'unknown')
                    op_direction = op.get('direction', 'unknown')
                    op_status = op.get('status', 'unknown')
                    op_label = op.get('label', 'N/A')
                    op_amount = op.get('amount', 0)
                    op_datetime = op.get('datetime', 'N/A')
                    
                    # Логируем все ключи операции для отладки (только для первой операции)
                    if i == 0:
                        yoomoney_logger.debug(f"Operation keys: {list(op.keys())}")
                    
                    yoomoney_logger.info(
                        f"Operation {i+1}/{len(operations)}: "
                        f"id={op_id}, type={op_type}, direction={op_direction}, "
                        f"status={op_status}, label={op_label[:80] if op_label != 'N/A' else 'N/A'}, "
                        f"amount={op_amount}, datetime={op_datetime}"
                    )
                
                found_payments = []
                
                for operation in operations:
                    operation_id = operation.get("operation_id", "unknown")
                    direction = operation.get("direction", "")
                    operation_type = operation.get("type", "")
                    label = operation.get("label", "")
                    status = operation.get("status", "")
                    amount_value = operation.get("amount", 0)
                    
                    # Проверяем, что это входящий платёж (deposition)
                    if direction != "in":
                        yoomoney_logger.info(f"❌ Skipping operation {operation_id}: direction={direction} (not 'in')")
                        continue
                    
                    # Проверяем тип операции - должен быть deposition или incoming-transfer
                    # Согласно документации: deposition - пополнение, incoming-transfer - входящий перевод
                    if operation_type not in ["deposition", "incoming-transfer"]:
                        yoomoney_logger.info(f"❌ Skipping operation {operation_id}: type={operation_type} (not deposition/incoming-transfer)")
                        continue
                    
                    # Проверяем статус - должен быть success
                    if status != "success":
                        yoomoney_logger.info(f"❌ Skipping operation {operation_id}: status={status} (not 'success')")
                        continue
                    
                    # Проверяем метку (label)
                    if not label:
                        yoomoney_logger.info(f"❌ Skipping operation {operation_id}: no label")
                        continue
                    
                    if not label.startswith(self.label_prefix):
                        yoomoney_logger.info(f"❌ Skipping operation {operation_id}: label '{label[:50]}...' doesn't start with '{self.label_prefix}'")
                        continue
                    
                    yoomoney_logger.info(f"✅ Operation {operation_id} passed all filters! Processing...")
                    
                    # Проверяем сумму
                    amount_value = operation.get("amount", 0)
                    try:
                        amount = float(amount_value)
                    except (ValueError, TypeError):
                        yoomoney_logger.warning(f"Invalid amount format: {amount_value}")
                        continue
                    
                    if amount <= 0:
                        continue
                    
                    # Извлекаем информацию о платеже
                    operation_id = operation.get("operation_id", "")
                    datetime_str = operation.get("datetime", "")
                    
                    user_id = self._extract_user_id_from_label(label)
                    package_key = self._extract_package_key_from_label(label)
                    
                    if not user_id or not package_key:
                        yoomoney_logger.warning(f"Failed to extract user_id or package_key from label: {label}")
                        continue
                    
                    payment_info = {
                        "label": label,
                        "amount": amount,
                        "operation_id": operation_id,
                        "datetime": datetime_str,
                        "user_id": user_id,
                        "package_key": package_key,
                        "status": status
                    }
                    
                    found_payments.append(payment_info)
                    yoomoney_logger.info(
                        f"✅ Found successful payment: label={label}, amount={amount}, "
                        f"user_id={user_id}, package={package_key}, operation_id={operation_id}"
                    )
                
                if found_payments:
                    yoomoney_logger.info(f"✅ Found {len(found_payments)} successful payments to process")
                    for payment in found_payments:
                        yoomoney_logger.info(
                            f"  - Label: {payment['label']}, User: {payment['user_id']}, "
                            f"Amount: {payment['amount']}, Package: {payment['package_key']}"
                        )
                else:
                    yoomoney_logger.debug("No payments found matching criteria (label prefix, status=success, direction=in)")
                
                return found_payments
                
        except httpx.TimeoutException:
            yoomoney_logger.error("Timeout while checking YooMoney payments")
            return []
        except Exception as e:
            yoomoney_logger.error(f"Error checking payments: {e}", exc_info=True)
            return []
    
    def _extract_user_id_from_label(self, label: str) -> Optional[int]:
        """Извлекает user_id из метки."""
        try:
            # Формат: tarot_luna_user_123456789_pkg_buy_2
            parts = label.split("_")
            if "user" in parts:
                idx = parts.index("user")
                if idx + 1 < len(parts):
                    return int(parts[idx + 1])
        except (ValueError, IndexError):
            pass
        return None
    
    def _extract_package_key_from_label(self, label: str) -> Optional[str]:
        """Извлекает package_key из метки.
        
        Формат label: {prefix}user_{user_id}_pkg_{package_key}_{timestamp}_{random}
        Пример: tarot_luna_user_123_pkg_buy_1_1734123456789_5678
        """
        try:
            parts = label.split("_")
            if "pkg" in parts:
                idx = parts.index("pkg")
                if idx + 1 < len(parts):
                    # package_key может содержать подчеркивания (например, buy_1)
                    # Берем все части после "pkg" до timestamp (если есть)
                    remaining = parts[idx + 1:]
                    # Если есть timestamp (число), берем все до него
                    package_parts = []
                    for part in remaining:
                        # Если это число (timestamp или random), останавливаемся
                        # timestamp обычно длинный (13+ цифр), random - 4 цифры
                        if part.isdigit():
                            if len(part) >= 10:  # timestamp
                                break
                            elif len(part) == 4:  # random suffix
                                break
                        package_parts.append(part)
                    if package_parts:
                        return "_".join(package_parts)
        except (ValueError, IndexError):
            pass
        return None
    
    async def get_operation_details(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает детальную информацию об операции по operation_id.
        
        Args:
            operation_id: ID операции из operation-history
            
        Returns:
            Детальная информация об операции или None
        """
        if not self.token:
            yoomoney_logger.warning("YooMoney token not set, cannot get operation details")
            return None
        
        try:
            url = f"{self.API_BASE_URL}/operation-details"
            
            form_data = {
                "operation_id": operation_id
            }
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            timeout = httpx.Timeout(30.0, connect=30.0)

            last_exc: Optional[Exception] = None
            for attempt in range(1, 4):
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(url, data=form_data, headers=headers)

                    if response.status_code != 200:
                        yoomoney_logger.error(
                            f"Failed to get operation details: {response.status_code} - {response.text[:300]}"
                        )
                        return None

                    data = response.json()

                    if "error" in data:
                        yoomoney_logger.error(
                            f"YooMoney API error in operation-details: {data.get('error')}"
                        )
                        return None

                    return data
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    last_exc = e
                    if attempt < 3:
                        await asyncio.sleep(0.6 * attempt)
                        continue
                except Exception as e:
                    yoomoney_logger.error(f"Error getting operation details: {e}", exc_info=True)
                    return None

            yoomoney_logger.error(
                f"Error getting operation details after retries (operation_id={operation_id}): {last_exc}",
                exc_info=True,
            )
            return None
                
        except Exception as e:
            yoomoney_logger.error(f"Error getting operation details: {e}", exc_info=True)
            return None
    
    async def get_package_info(self, package_key: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о пакете по ключу из базы данных или конфига."""
        try:
            from database import db
            rate = await db.get_rate(package_key)
            
            if rate:
                return {
                    "requests": rate["requests"],
                    "price": rate["price"],
                    "label": rate.get("label", f"{rate['requests']} запросов ({rate['price']} руб.)")
                }
        except Exception:
            pass
        
        # Fallback на конфиг
        return PAYMENT_OPTIONS.get(package_key)


# Глобальный экземпляр
yoomoney_payment = YooMoneyPayment()