import logging
import requests
import re
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)

# --- Конфигурация ---
API_ID = 
API_HASH = "
BOT_TOKEN = "

# API ключи Яндекс
GEOCODER_API_KEY = ""
STATIC_API_KEY = "c3bbd5"
RASP_API_KEY = "00a64e8ac4"
RASP_API_BASE_URL = "https:3.0"

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

# Инициализация клиента Pyrogram
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# --- Логика Яндекс API (остается без изменений) ---

def get_station_code(station_name: str) -> str | None:
    """Находит код станции по ее названию."""
    url = f"{RASP_API_BASE_URL}/stations_list/"
    params = {"apikey": RASP_API_KEY, "lang": "ru_RU", "format": "json"}
    try:
        response = requests.get(url)
        response.raise_for_status()
        countries = response.json().get("countries", [])
        for country in countries:
            for region in country.get("regions", []):
                for settlement in region.get("settlements", []):
                    for station in settlement.get("stations", []):
                        if station_name.lower() in station.get("title", "").lower():
                            return station.get("codes", {}).get("yandex_code")
    except requests.RequestException as e:
        log.error(f"Ошибка при поиске кода станции: {e}")
    return None

def search_schedule(from_station: str, to_station: str, transport_type: str):
    """Ищет расписание между двумя станциями."""
    from_code = get_station_code(from_station)
    to_code = get_station_code(to_station)
    if not from_code or not to_code:
        return None
    params = {
        "apikey": RASP_API_KEY, "format": "json", "from": from_code,
        "to": to_code, "transport_types": transport_type, "limit": 10,
    }
    try:
        response = requests.get(f"{RASP_API_BASE_URL}/search/", params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        log.error(f"Ошибка при поиске расписания: {e}")
        return None

def get_coordinates_by_address(address: str) -> tuple[str, str] | None:
    """Получает координаты по адресу через Яндекс.Геокодер."""
    params = {"apikey": GEOCODER_API_KEY, "geocode": address, "format": "json"}
    try:
        response = requests.get("https://geocode-maps.yandex.ru/1.x/", params=params)
        response.raise_for_status()
        data = response.json()
        pos = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["Point"]["pos"]
        return pos.split()
    except (requests.RequestException, IndexError, KeyError) as e:
        log.error(f"Ошибка при получении координат: {e}")
        return None

def get_static_map_url(lon, lat, zoom) -> str:
    """Формирует URL для Яндекс.Static API."""
    return (
        f"https://static-maps.yandex.ru/1.x/?"
        f"ll={lon},{lat}&z={zoom}&l=map&size=650,450&scale=1.5"
        f"&pt={lon},{lat},pm2vvm&lang=ru_RU"
    )


# --- Клавиатуры ---

def get_zoom_keyboard(lon, lat, zoom):
    """Возвращает клавиатуру с кнопками зума."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("➕", callback_data=f"zoom_in:{lon}:{lat}:{zoom}"),
        InlineKeyboardButton("➖", callback_data=f"zoom_out:{lon}:{lat}:{zoom}"),
    ]])


# --- Обработчики Pyrogram ---

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Обработчик команды /start."""
    user = message.from_user
    await message.reply_html(
        f"Привет, {user.mention}!\n\n"
        f"Я многофункциональный бот! Вот что я умею:\n"
        f"- <b>Карта по адресу:</b> Отправь мне адрес.\n"
        f"- <b>Координаты:</b> Напиши 'координаты [адрес]'.\n"
        f"- <b>Расписание электричек:</b> Напиши 'электричка [станция отпр.] - [станция приб.]'.\n"
        f"- <b>Расписание автобусов:</b> Напиши 'автобус [номер] [станция отпр.] - [станция приб.]'."
    )

@app.on_message(filters.location)
async def handle_location(client: Client, message: Message):
    """Обработчик геолокации."""
    location = message.location
    log.info(f"Получена геолокация: {location.latitude}, {location.longitude}")
    await send_map_for_coords(client, message, location.longitude, location.latitude)


@app.on_message(filters.text & ~filters.command("start"))
async def handle_text(client: Client, message: Message):
    """Обработчик текстовых сообщений."""
    text = message.text.lower()
    log.info(f"Получено сообщение: {text}")

    train_match = re.match(r"электричка\s+(.+?)\s*-\s*(.+)", text)
    bus_match = re.match(r"автобус\s+(\d+)\s+(.+?)\s*-\s*(.+)", text)

    if train_match:
        from_station, to_station = train_match.groups()
        schedule = search_schedule(from_station.strip(), to_station.strip(), "suburban")
        if schedule and schedule.get("segments"):
            response_text = f"<b>Расписание электричек от {from_station.title()} до {to_station.title()}:</b>\n"
            for segment in schedule["segments"]:
                departure_time = segment["departure"].split("T")[1][:5]
                response_text += f"- Отправление в {departure_time}\n"
            await message.reply_html(response_text)
        else:
            await message.reply_text("Не удалось найти расписание для этого маршрута.")

    elif bus_match:
        route_num, from_station, to_station = bus_match.groups()
        schedule = search_schedule(from_station.strip(), to_station.strip(), "bus")
        if schedule and schedule.get("segments"):
            response_text = f"<b>Расписание автобуса №{route_num} от {from_station.title()} до {to_station.title()}:</b>\n"
            for segment in schedule["segments"]:
                if segment["thread"]["number"] == route_num:
                    departure_time = segment["departure"].split("T")[1][:5]
                    response_text += f"- Отправление в {departure_time}\n"
            if len(response_text.splitlines()) > 1:
                await message.reply_html(response_text)
            else:
                await message.reply_text(f"Не найдено рейсов для маршрута №{route_num}.")
        else:
            await message.reply_text("Не удалось найти расписание для этого маршрута.")

    elif text.startswith("координаты "):
        address = text[11:]
        coords = get_coordinates_by_address(address)
        if coords:
            lon, lat = coords
            await message.reply_text(f"Координаты для '{address}':\nДолгота: {lon}\nШирота: {lat}")
        else:
            await message.reply_text("Не удалось найти координаты.")
    else:
        await send_map_for_address(client, message, text)


@app.on_callback_query()
async def button_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик нажатий на инлайн-кнопки (зум)."""
    log.info(f"Получены данные с кнопки: {callback_query.data}")
    try:
        action, lon_str, lat_str, zoom_str = callback_query.data.split(":")
        lon, lat, zoom = float(lon_str), float(lat_str), int(zoom_str)
        log.info(f"Распарсенные данные: action={action}, lon={lon}, lat={lat}, zoom={zoom}")
    except ValueError as e:
        log.error(f"Ошибка парсинга данных с кнопки: {e}")
        await callback_query.answer("Ошибка!", show_alert=True)
        return

    if action == "zoom_in":
        zoom = min(17, zoom + 1)
    elif action == "zoom_out":
        zoom = max(0, zoom - 1)
    
    log.info(f"Новый зум: {zoom}")
    map_url = get_static_map_url(lon, lat, zoom)
    log.info(f"Новый URL карты: {map_url}")
    keyboard = get_zoom_keyboard(lon, lat, zoom)

    await callback_query.edit_message_media(
        media=InputMediaPhoto(media=map_url),
        reply_markup=keyboard
    )
    await callback_query.answer()


# --- Вспомогательные функции для отправки карт ---

async def send_map_for_address(client: Client, message: Message, address: str):
    """Находит координаты по адресу и отправляет карту."""
    coords = get_coordinates_by_address(address)
    if coords:
        lon, lat = coords
        await send_map_for_coords(client, message, lon, lat, caption=f"Карта для '{address}'")
    else:
        await message.reply_text("Не удалось найти это место.")

async def send_map_for_coords(client: Client, message: Message, lon: float, lat: float, caption="Ваше местоположение"):
    """Отправляет статическую карту по координатам с кнопками зума."""
    zoom = 13
    map_url = get_static_map_url(lon, lat, zoom)
    keyboard = get_zoom_keyboard(lon, lat, zoom)
    await message.reply_photo(photo=map_url, caption=caption, reply_markup=keyboard)


if __name__ == "__main__":
    print("Бот запускается...")
    app.run()
    print("Бот остановлен.")
