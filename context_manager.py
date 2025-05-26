import json
import time
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class GenerationRecord:
    """Класс для хранения информации о сгенерированном посте."""
    
    def __init__(self, theme: str, format: str, ending: str, 
                 additional_instructions: Optional[Dict] = None,
                 post_text: Optional[str] = None):
        self.theme = theme
        self.format = format
        self.ending = ending
        self.additional_instructions = additional_instructions or {}
        self.post_text = post_text
        self.timestamp = int(time.time())
    
    def to_dict(self) -> Dict:
        """Преобразует запись в словарь для сохранения."""
        return {
            'theme': self.theme,
            'format': self.format,
            'ending': self.ending,
            'additional_instructions': self.additional_instructions,
            'post_text': self.post_text,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GenerationRecord':
        """Создает запись из словаря."""
        return cls(
            theme=data['theme'],
            format=data['format'],
            ending=data['ending'],
            additional_instructions=data.get('additional_instructions'),
            post_text=data.get('post_text')
        )

class ContextManager:
    """Класс для управления контекстом генерации постов."""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.generation_history: List[GenerationRecord] = []
        self.theme_frequency: Dict[str, int] = {}
        self.format_frequency: Dict[str, int] = {}
    
    def add_generation(self, params: Dict, post_text: str) -> None:
        """
        Добавляет новую генерацию в историю.
        
        Args:
            params: Параметры генерации (тема, формат, окончание и т.д.)
            post_text: Текст сгенерированного поста
        """
        # Создаем новую запись
        record = GenerationRecord(
            theme=params['theme'],
            format=params['format'],
            ending=params['ending'],
            additional_instructions=params.get('additional_instructions'),
            post_text=post_text
        )
        
        # Добавляем в историю
        self.generation_history.append(record)
        
        # Обновляем частоту использования тем и форматов
        self.theme_frequency[record.theme] = self.theme_frequency.get(record.theme, 0) + 1
        self.format_frequency[record.format] = self.format_frequency.get(record.format, 0) + 1
        
        # Ограничиваем размер истории
        if len(self.generation_history) > self.max_history:
            old_record = self.generation_history.pop(0)
            # Уменьшаем счетчики частоты
            self.theme_frequency[old_record.theme] -= 1
            self.format_frequency[old_record.format] -= 1
            # Удаляем нулевые значения
            if self.theme_frequency[old_record.theme] == 0:
                del self.theme_frequency[old_record.theme]
            if self.format_frequency[old_record.format] == 0:
                del self.format_frequency[old_record.format]
        
        # Сохраняем историю в файл
        self._save_history()
    
    def get_context(self) -> Dict:
        """
        Возвращает контекст для генерации нового поста.
        
        Returns:
            Dict с информацией о последних генерациях и статистикой
        """
        return {
            'last_generations': [
                record.to_dict() for record in self.generation_history[-3:]
            ],
            'theme_frequency': self.theme_frequency,
            'format_frequency': self.format_frequency
        }
    
    def _save_history(self) -> None:
        """Сохраняет историю генераций в JSON файл."""
        try:
            with open('generation_history.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'history': [record.to_dict() for record in self.generation_history],
                    'theme_frequency': self.theme_frequency,
                    'format_frequency': self.format_frequency
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении истории генераций: {str(e)}")
    
    def load_history(self) -> None:
        """Загружает историю генераций из JSON файла."""
        try:
            with open('generation_history.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.generation_history = [
                    GenerationRecord.from_dict(record)
                    for record in data.get('history', [])
                ]
                self.theme_frequency = data.get('theme_frequency', {})
                self.format_frequency = data.get('format_frequency', {})
        except FileNotFoundError:
            logger.info("Файл истории генераций не найден, начинаем с пустой истории")
        except Exception as e:
            logger.error(f"Ошибка при загрузке истории генераций: {str(e)}")
            self.generation_history = []
            self.theme_frequency = {}
            self.format_frequency = {} 