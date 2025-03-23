"""
Модуль планировщика для автоматической генерации и публикации постов по расписанию.
"""

import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import time
import random
from typing import List, Dict, Optional

from config import TIMEZONE, CHANNEL_ID
from schedule_config import SCHEDULE_CONFIG
from deepseek_client import DeepSeekClient
from database import Database

# Настройка логирования
logger = logging.getLogger('scheduler')
logger.setLevel(logging.INFO)

# Получаем часовой пояс
tz = pytz.timezone(TIMEZONE)

class PostScheduler:
    """Планировщик для генерации и публикации постов по расписанию."""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.deepseek_client = DeepSeekClient()
        self.config = SCHEDULE_CONFIG
        self.running = False
        self.next_check_time = None
        logger.info(f"Инициализация планировщика. Конфигурация: {self.config}")
        
    async def start(self):
        """Запускает планировщик."""
        if self.running:
            logger.warning("Планировщик уже запущен.")
            return
        
        self.running = True
        logger.info("Планировщик запущен.")
        
        # Если настроено, генерируем пост на старте
        if self.config["generate_on_startup"] and self.is_within_schedule():
            logger.info("Запуск с генерацией поста на старте (generate_on_startup=True)")
            await self.schedule_next_post(force=True)
        
        # Запускаем основной цикл планировщика
        await self.scheduler_loop()
    
    async def stop(self):
        """Останавливает планировщик."""
        self.running = False
        logger.info("Планировщик остановлен.")
    
    def is_within_schedule(self, dt: Optional[datetime] = None) -> bool:
        """Проверяет, находится ли указанное время в рамках расписания."""
        if not self.config["enabled"]:
            logger.info("Автоматическое планирование выключено в конфигурации.")
            return False
        
        if dt is None:
            dt = datetime.now(tz)
        
        # Проверяем, является ли день подходящим
        if dt.weekday() not in self.config["days_of_week"]:
            logger.debug(f"День {dt.weekday()} не входит в расписание дней недели {self.config['days_of_week']}")
            return False
        
        # Если указаны конкретные времена, проверяем их
        if self.config["specific_times"]:
            for time_spec in self.config["specific_times"]:
                if dt.hour == time_spec["hour"] and dt.minute == time_spec["minute"]:
                    logger.debug(f"Время {dt.hour}:{dt.minute} соответствует расписанию")
                    return True
            logger.debug(f"Время {dt.hour}:{dt.minute} не соответствует расписанию")
            return False
        
        # Проверяем, находится ли время в диапазоне start_time - end_time
        start_hour = self.config["start_time"]["hour"]
        start_minute = self.config["start_time"]["minute"]
        end_hour = self.config["end_time"]["hour"]
        end_minute = self.config["end_time"]["minute"]
        
        start_time = dt.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        end_time = dt.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        
        is_within = start_time <= dt <= end_time
        logger.debug(f"Проверка времени {dt.hour}:{dt.minute} в диапазоне {start_hour}:{start_minute}-{end_hour}:{end_minute}: {is_within}")
        return is_within
    
    def calculate_next_post_time(self) -> Optional[datetime]:
        """Рассчитывает время следующей публикации."""
        now = datetime.now(tz)
        logger.info(f"Расчет следующего времени публикации. Текущее время: {now}")
        
        # Если указаны конкретные времена публикаций
        if self.config["specific_times"]:
            next_times = []
            for day_offset in range(7):  # Проверяем на неделю вперед
                check_date = now.date() + timedelta(days=day_offset)
                check_weekday = check_date.weekday()
                
                if check_weekday in self.config["days_of_week"]:
                    for time_spec in self.config["specific_times"]:
                        post_time = datetime(
                            check_date.year, 
                            check_date.month, 
                            check_date.day, 
                            time_spec["hour"], 
                            time_spec["minute"], 
                            0
                        )
                        post_time = tz.localize(post_time)
                        
                        if post_time > now:
                            next_times.append(post_time)
            
            if next_times:
                next_time = min(next_times)
                logger.info(f"Следующее время публикации (specific_times): {next_time}")
                return next_time
            logger.warning("Не найдено следующего времени публикации в specific_times")
            return None
        
        # Если используются интервалы
        interval = self.config["interval_minutes"]
        logger.info(f"Используется интервал: {interval} минут")
        
        # Начинаем с текущего дня
        day_offset = 0
        while day_offset < 7:  # Ищем в пределах недели
            check_date = now.date() + timedelta(days=day_offset)
            check_weekday = check_date.weekday()
            
            if check_weekday in self.config["days_of_week"]:
                # Начальное время публикаций для этого дня
                start_time = datetime(
                    check_date.year, 
                    check_date.month, 
                    check_date.day, 
                    self.config["start_time"]["hour"], 
                    self.config["start_time"]["minute"], 
                    0
                )
                start_time = tz.localize(start_time)
                
                # Конечное время публикаций для этого дня
                end_time = datetime(
                    check_date.year, 
                    check_date.month, 
                    check_date.day, 
                    self.config["end_time"]["hour"], 
                    self.config["end_time"]["minute"], 
                    0
                )
                end_time = tz.localize(end_time)
                
                logger.debug(f"Проверка дня {check_date}: start_time={start_time}, end_time={end_time}")
                
                # Если мы уже прошли конечное время сегодня, переходим к следующему дню
                if now > end_time and day_offset == 0:
                    logger.debug("Текущее время после end_time, переходим к следующему дню")
                    day_offset += 1
                    continue
                
                # Если мы находимся перед началом сегодня, следующая публикация - в начале
                if now < start_time:
                    logger.info(f"Следующая публикация в начале дня: {start_time}")
                    return start_time
                
                # Вычисляем следующее время публикации
                minutes_since_start = (now - start_time).total_seconds() / 60
                intervals_passed = int(minutes_since_start / interval)
                
                # Следующий интервал
                next_interval = (intervals_passed + 1) * interval
                next_time = start_time + timedelta(minutes=next_interval)
                
                logger.debug(f"Интервалов прошло: {intervals_passed}, следующий интервал: {next_interval}")
                
                # Если следующее время не превышает конечное время, возвращаем его
                if next_time <= end_time:
                    logger.info(f"Следующее время публикации: {next_time}")
                    return next_time
            
            # Переходим к следующему дню
            day_offset += 1
        
        logger.warning("Не удалось найти следующее время публикации")
        return None
    
    async def generate_post(self) -> Optional[str]:
        """Генерирует новый пост с помощью DeepSeek API."""
        # Оборачиваем синхронный вызов в асинхронную функцию
        loop = asyncio.get_running_loop()
        post = await loop.run_in_executor(None, self.deepseek_client.generate_post)
        return post
    
    async def schedule_next_post(self, force: bool = False):
        """Планирует следующий пост для публикации."""
        if not self.config["enabled"] and not force:
            logger.info("Автоматическое планирование выключено в конфигурации.")
            return
        
        next_time = self.calculate_next_post_time()
        
        if not next_time and not force:
            logger.warning("Не удалось рассчитать время следующей публикации.")
            return
        
        # Если force=True и next_time is None, используем текущее время + 1 минута
        if force and not next_time:
            next_time = datetime.now(tz) + timedelta(minutes=1)
        
        # Всегда генерируем новый пост для максимального разнообразия
        logger.info("Генерация нового поста...")
        post_text = await self.generate_post()
        
        if not post_text:
            logger.error("Не удалось получить текст поста.")
            return
        
        try:
            # Добавляем пост в расписание
            post_id = self.db.add_scheduled_post(next_time, post_text, is_auto_generated=True)
            
            logger.info(f"Запланирован автоматический пост (id={post_id}) на {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Если это принудительная публикация (force=True), публикуем сразу
            if force:
                try:
                    await self.bot.send_message(CHANNEL_ID, post_text)
                    self.db.mark_post_as_sent(post_id)
                    logger.info(f"Пост {post_id} успешно опубликован")
                except Exception as e:
                    logger.error(f"Ошибка при публикации поста {post_id}: {str(e)}")
            
            return post_id
        except Exception as e:
            logger.error(f"Ошибка при планировании поста: {str(e)}")
            return None
    
    async def scheduler_loop(self):
        """Основной цикл планировщика."""
        logger.info("Запуск основного цикла планировщика")
        while self.running:
            try:
                # Проверяем, нужно ли планировать следующий пост
                if not self.next_check_time or datetime.now(tz) >= self.next_check_time:
                    logger.info("Проверка необходимости планирования следующего поста")
                    
                    # Планируем следующий пост
                    if self.is_within_schedule():
                        await self.schedule_next_post()
                    
                    # Устанавливаем время следующей проверки через 5 минут
                    self.next_check_time = datetime.now(tz) + timedelta(minutes=5)
                    logger.info(f"Следующая проверка запланирована на {self.next_check_time}")
                
                # Удаляем старые отправленные посты
                self.db.clean_old_sent_posts()
                
                # Спим 60 секунд
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле планировщика: {str(e)}")
                await asyncio.sleep(60)  # В случае ошибки тоже ждем 60 секунд 