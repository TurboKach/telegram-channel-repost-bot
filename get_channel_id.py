import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Привет! Я бот для определения ID чатов и каналов.\n\n"
        "📋 Просто перешли мне любое сообщение из чата или канала, "
        "и я покажу его ID!"
    )

@dp.message()
async def forward_handler(message: Message):
    """Обработчик пересланных сообщений"""
    
    # Проверяем, является ли сообщение пересланным
    if message.forward_from_chat:
        chat = message.forward_from_chat
        
        # Определяем тип чата
        chat_type_emoji = {
            'private': '👤',
            'group': '👥', 
            'supergroup': '🏢',
            'channel': '📢'
        }
        
        emoji = chat_type_emoji.get(chat.type, '❓')
        
        # Формируем ответ
        response = f"{emoji} **Информация о чате:**\n\n"
        response += f"🆔 **ID:** `{chat.id}`\n"
        response += f"📝 **Название:** {chat.title or 'Не указано'}\n"
        response += f"🏷 **Тип:** {chat.type}\n"
        
        if chat.username:
            response += f"🔗 **Username:** @{chat.username}\n"
        
        await message.answer(response, parse_mode='Markdown')
        
    elif message.forward_from:
        # Если сообщение переслано от пользователя
        user = message.forward_from
        response = f"👤 **Сообщение переслано от пользователя:**\n\n"
        response += f"🆔 **ID пользователя:** `{user.id}`\n"
        response += f"👤 **Имя:** {user.first_name}"
        
        if user.last_name:
            response += f" {user.last_name}"
            
        if user.username:
            response += f"\n🔗 **Username:** @{user.username}"
            
        await message.answer(response, parse_mode='Markdown')
        
    else:
        # Если сообщение не переслано
        await message.answer(
            "❌ Это сообщение не является пересланным.\n\n"
            "📩 Перешли мне сообщение из любого чата или канала, "
            "чтобы узнать его ID!"
        )

async def main():
    """Главная функция для запуска бота"""
    try:
        print("🤖 Бот запускается...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
