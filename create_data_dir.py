import os

# Создаем папку data, если её нет
os.makedirs('data', exist_ok=True)

# Создаем пустой .gitkeep файл
with open('data/.gitkeep', 'w') as f:
    pass 