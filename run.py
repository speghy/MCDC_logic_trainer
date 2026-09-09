"""
Точка входа для запуска приложения
"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic_trainer.main import main

if __name__ == "__main__":
    main()