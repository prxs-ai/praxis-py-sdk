#!/usr/bin/env python3
"""
Простой анализатор текста для тестирования системы Praxis.
Анализирует файл и возвращает статистику: количество букв, слов, строк.
"""

import sys
import os
import re
from pathlib import Path


def analyze_text(file_path):
    """Анализирует текстовый файл и возвращает статистику."""
    try:
        # Читаем файл
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Подсчитываем статистику
        char_count = len(content)
        
        # Только буквы (кириллица + латиница)
        letter_count = len(re.findall(r'[а-яё\w]', content, re.IGNORECASE))
        
        # Слова (разделенные пробелами и знаками препинания)
        word_count = len(re.findall(r'\b\w+\b', content))
        
        # Строки
        line_count = len(content.split('\n'))
        
        # Пробелы
        space_count = content.count(' ')
        
        # Формируем результат
        result = {
            'файл': file_path,
            'всего_символов': char_count,
            'букв': letter_count,
            'слов': word_count,
            'строк': line_count,
            'пробелов': space_count
        }
        
        return result
        
    except Exception as e:
        return {'ошибка': str(e)}


def main():
    """Основная функция анализатора."""
    
    # Получаем путь к файлу из переменных окружения или аргументов
    file_path = None
    
    # Сначала проверяем переменные окружения (для Docker)
    if 'ARG_FILE_PATH' in os.environ:
        file_path = os.environ['ARG_FILE_PATH']
    elif 'ARG_FILENAME' in os.environ:
        # Если передали только имя файла, ищем в /shared
        filename = os.environ['ARG_FILENAME']
        file_path = f'/shared/{filename}'
    
    # Если не нашли в env, берем из аргументов командной строки
    if not file_path and len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    # По умолчанию анализируем test_text.txt
    if not file_path:
        file_path = '/shared/test_text.txt'
    
    # Анализируем файл
    result = analyze_text(file_path)
    
    # Выводим результат в удобочитаемом виде
    print("=" * 50)
    print("📊 АНАЛИЗ ТЕКСТА")
    print("=" * 50)
    
    if 'ошибка' in result:
        print(f"❌ Ошибка: {result['ошибка']}")
        return 1
    
    print(f"📁 Файл: {result['файл']}")
    print(f"📝 Всего символов: {result['всего_символов']}")
    print(f"🔤 Букв: {result['букв']}")
    print(f"💬 Слов: {result['слов']}")
    print(f"📄 Строк: {result['строк']}")
    print(f"⭐ Пробелов: {result['пробелов']}")
    print("=" * 50)
    print("✅ АНАЛИЗ ЗАВЕРШЕН")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())