async def schedule_posts():
    """Функция для публикации постов по расписанию."""
    logger.info("Запуск планировщика публикаций")
    
    while True:
        try:
            if SCHEDULE_CONFIG["enabled"]:
                current_time = datetime.now(tz)
                logger.info(f"Текущее время: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"День недели: {current_time.weekday()}")
                
                # Проверяем, нужно ли публиковать пост сейчас
                if SCHEDULE_CONFIG["specific_times"]:
                    logger.info("Проверка конкретных времен публикации")
                    # Проверяем конкретные времена
                    for time_spec in SCHEDULE_CONFIG["specific_times"]:
                        logger.info(f"Проверка времени: {time_spec['hour']}:{time_spec['minute']}")
                        if (current_time.hour == time_spec["hour"] and 
                            current_time.minute == time_spec["minute"] and 
                            current_time.weekday() in SCHEDULE_CONFIG["days_of_week"]):
                            logger.info("Условия для публикации выполнены")
                            await publish_scheduled_post()
                        else:
                            logger.info("Условия для публикации не выполнены")
                else:
                    logger.info("Проверка интервалов публикации")
                    # Проверяем интервалы
                    start_time = current_time.replace(
                        hour=SCHEDULE_CONFIG["start_time"]["hour"],
                        minute=SCHEDULE_CONFIG["start_time"]["minute"],
                        second=0,
                        microsecond=0
                    )
                    end_time = current_time.replace(
                        hour=SCHEDULE_CONFIG["end_time"]["hour"],
                        minute=SCHEDULE_CONFIG["end_time"]["minute"],
                        second=0,
                        microsecond=0
                    )
                    
                    logger.info(f"Время начала: {start_time.strftime('%H:%M')}")
                    logger.info(f"Время окончания: {end_time.strftime('%H:%M')}")
                    
                    if (start_time <= current_time <= end_time and 
                        current_time.weekday() in SCHEDULE_CONFIG["days_of_week"]):
                        # Проверяем, кратно ли текущее время интервалу публикации
                        current_minutes = current_time.hour * 60 + current_time.minute
                        logger.info(f"Текущее время в минутах: {current_minutes}")
                        logger.info(f"Интервал публикации: {SCHEDULE_CONFIG['interval_minutes']}")
                        
                        if current_minutes % SCHEDULE_CONFIG["interval_minutes"] == 0:
                            logger.info("Условия для публикации выполнены")
                            await publish_scheduled_post()
                        else:
                            logger.info("Условия для публикации не выполнены")
                    else:
                        logger.info("Текущее время вне диапазона публикации")
            
            # Ждем 1 минуту перед следующей проверкой
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {str(e)}")
            await asyncio.sleep(60)
