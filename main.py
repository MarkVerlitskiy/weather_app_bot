import requests
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

BOT_TOKEN = "7349205212:AAF-pvCL_gw74yqg6ZEvTJiuEHlBd0j87TU"
ACCUWEATHER_API_KEY = "E3WJYpzMKzxNBlk0UJRxpd72L2DVJV24"
ACCUWEATHER_BASE_URL = "http://dataservice.accuweather.com"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_state = {}


def create_interval_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Прогноз на 1 день", callback_data="interval_1")],
        [InlineKeyboardButton(text="Прогноз на 5 дней", callback_data="interval_5")]
    ])
    return keyboard


def get_location_key(city_name):
    url = f"{ACCUWEATHER_BASE_URL}/locations/v1/cities/search"
    params = {"apikey": ACCUWEATHER_API_KEY, "q": city_name}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    if data:
        return data[0]["Key"]
    else:
        raise ValueError(f"Город '{city_name}' не найден.")


def get_weather_forecast(location_key, days):
    url = f"{ACCUWEATHER_BASE_URL}/forecasts/v1/daily/{days}day/{location_key}"
    params = {"apikey": ACCUWEATHER_API_KEY, "metric": True}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_state[message.from_user.id] = {"route": [], "interval": None}
    await message.answer(
        "Привет! Я бот прогноза погоды. Используйте /help, чтобы узнать мои команды.\n"
        "Начните с выбора временного интервала прогноза, нажав на одну из кнопок ниже.",
        reply_markup=create_interval_keyboard()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🤖 Я — бот прогноза погоды, предоставляющий точные данные о погоде в разных точках маршрута.\n\n"
        "Команды:\n"
        "/start — Начать работу с ботом и выбрать временной интервал прогноза.\n"
        "/help — Узнать о функциях бота.\n"
        "/weather — Указать маршрут (начальный, конечный, промежуточные точки) и получить прогноз.\n\n"
        "Как пользоваться:\n"
        "1. Введите команду /start или /weather.\n"
        "2. Выберите временной интервал (1 или 5 дней).\n"
        "3. Укажите маршрут, введя названия городов (один за другим).\n"
        "4. Получите прогноз для каждой точки маршрута в удобном формате."
    )
    await message.answer(help_text)


@dp.message(Command("weather"))
async def cmd_weather(message: Message):
    user_state[message.from_user.id] = {"route": [], "interval": None}
    await message.answer(
        "Выберите временной интервал для прогноза погоды:",
        reply_markup=create_interval_keyboard()
    )


@dp.callback_query(F.data.startswith("interval_"))
async def handle_interval_selection(callback: CallbackQuery):
    interval = 1 if "interval_1" in callback.data else 5
    user_state[callback.from_user.id]["interval"] = interval
    await callback.message.answer(
        f"Вы выбрали прогноз на {interval} день\n"
        "Теперь введите начальный город вашего маршрута."
    )


@dp.message(F.text)
async def handle_route_input(message: Message):
    user_id = message.from_user.id
    state = user_state.get(user_id)

    if not state or state["interval"] is None:
        await message.answer(
            "Сначала выберите временной интервал прогноза через /start или /weather."
        )
        return

    if message.text.lower() == "готово":
        if len(state["route"]) < 2:
            await message.answer("Вы должны указать как минимум начальный и конечный города маршрута.")
        else:
            await generate_forecast(message, state)
        return

    state["route"].append(message.text.strip())
    if len(state["route"]) == 1:
        await message.answer("Введите конечный город вашего маршрута.")
    elif len(state["route"]) == 2:
        await message.answer(
            "Если есть промежуточные остановки, введите их. Когда закончите, напишите 'готово'."
        )
    else:
        await message.answer("Добавлен ещё один город. Продолжайте или напишите 'готово'.")


async def generate_forecast(message: Message, state):
    try:
        interval = state["interval"]
        route = state["route"]
        forecast_text = "Прогноз погоды для вашего маршрута:\n\n"

        for city in route:
            location_key = get_location_key(city)
            forecast = get_weather_forecast(location_key, interval)
            forecast_text += f"🌍 {city}:\n"

            for day in forecast["DailyForecasts"]:
                date = day["Date"][:10]
                min_temp = day["Temperature"]["Minimum"]["Value"]
                max_temp = day["Temperature"]["Maximum"]["Value"]
                conditions = day["Day"]["IconPhrase"]
                forecast_text += f"📅 {date}: {min_temp}°C - {max_temp}°C, {conditions}\n"

            forecast_text += "\n"

        await message.answer(forecast_text)
    except ValueError as e:
        await message.answer(str(e))
    except requests.RequestException:
        await message.answer("Ошибка при запросе данных AccuWeather. Попробуйте позже.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
