#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🍺 Mountain Brew — Telegram бот для приёма заказів v2.0
4 мови · знижки · сети · геолокація
"""

import logging
import os
import json
import urllib.request
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)

# ═══════════════════════════════════════════════════════════════
# ▼▼▼  НАЛАШТУВАННЯ  ▼▼▼
# ═══════════════════════════════════════════════════════════════

BOT_TOKEN = "8678700532:AAEQjkF60C9UmnsMMwuyWmtWSAesFyiPQAk"
ADMIN_CHAT_ID = 446520092
DELIVERY_COST = 5.0
MIN_ORDER_BOTTLES = 6

# Google Sheets — URL з Google Apps Script (див. інструкцію)
# Після налаштування таблиці вставте сюди URL
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzsiUHbsqgfbJeXStC2GjRPse_8csdWYmUMZdpWzLQsRPxboSG-PQtGNYegZkgh3TM/exec"  # ← сюди вставити URL

# ═══════════════════════════════════════════════════════════════
# АССОРТИМЕНТ
# Формат: (номер, назва, крепость, ціна, ціна_зі_знижкою_або_None, в_наявності)
# Якщо discount=None — знижки немає
# ═══════════════════════════════════════════════════════════════

BEER_MENU = [
    # (num, name,                           abv,     price, discount, available)
    (1,  "American Wheat",                  "6.0%",  2.50,  2.00,  True),
    (2,  "Belgian Wheat",                   "5.1%",  2.50,  2.00,  True),
    (3,  "Double IPA",                      "8.5%",  2.50,  None,  False),  # SOLD OUT
    (4,  "American Pale Ale",               "6.5%",  2.50,  2.00,  True),
    (5,  "White IPA",                       "6.1%",  2.50,  None,  True),
    (6,  "French Saison",                   "6.5%",  2.50,  2.00,  True),
    (7,  "Milk Stout Vanilla",              "5.8%",  2.50,  None,  False),  # SOLD OUT
    (8,  "Dark Mild Ale",                   "6.5%",  2.50,  None,  True),
    (9,  "Irish Red Ale Chili",             "6.8%",  2.50,  2.00,  True),
    (10, "Belgian Dubbel",                  "7.0%",  2.50,  2.00,  True),
    (11, "Belgian Tripel",                  "10.0%", 2.50,  None,  True),
    (12, "Rye IPA",                         "7.4%",  2.50,  2.00,  True),
    (13, "French Saison Strong",            "7.5%",  2.50,  2.00,  True),
    (14, "German Gose Classic",             "7.4%",  2.50,  2.00,  True),
    (15, "Costa Blanca Tomato Gose",        "7.4%",  2.50,  2.00,  True),
    (16, "Coconut Plombir Milkshake IPA",   "6.5%",  2.50,  2.00,  True),
    (17, "Bounti Pastry Stout",             "12.2%", 2.50,  2.00,  True),
    (18, "Summer Ale",                      "4.9%",  2.50,  None,  True),
    (19, "Khurma Double IPA",               "7.2%",  2.50,  None,  True),
    (20, "Finiki Double IPA",               "7.2%",  2.50,  None,  True),
    (21, "Dark Chocolate Dry Stout",        "5.3%",  2.50,  None,  True),
    (22, "Wheatwine",                       "11.0%", 2.50,  None,  True),
    (23, "Pecan Pastry Stout",              "12.0%", 2.50,  None,  True),
    (24, "Rauchbier",                       "5.7%",  2.50,  None,  True),
    (25, "Export Stout",                    "5.4%",  2.50,  None,  True),
    (26, "West Coast IPA",                  "6.6%",  2.50,  None,  True),
    (27, "Hazy IPA",                        "6.4%",  2.50,  None,  True),
    (28, "Brut Barleywine",                 "9.3%",  2.50,  None,  True),
    (29, "Belgian Kriek",                   "6.5%",  2.50,  None,  True),
    (30, "Imperial Stout 🆕",               "12.6%", 2.50,  None,  True),
]

# ═══════════════════════════════════════════════════════════════
# СЕТИ (набори)
# ═══════════════════════════════════════════════════════════════

BEER_SETS = [
    {
        "id": "set_all",
        "name": {
            "uk": "🍺 Спробуй все!",
            "ru": "🍺 Попробуй всё!",
            "en": "🍺 Try them all!",
            "es": "🍺 ¡Pruébalas todas!",
        },
        "desc": {
            "uk": "По 1 пляшці кожного сорту в наявності",
            "ru": "По 1 бутылке каждого сорта в наличии",
            "en": "1 bottle of every available beer",
            "es": "1 botella de cada cerveza disponible",
        },
        "beers": "ALL_AVAILABLE",
        "discount_pct": 30,
    },
    {
        "id": "set_sour",
        "name": {
            "uk": "🍋 Кислий сет",
            "ru": "🍋 Кислый сет",
            "en": "🍋 Sour Set",
            "es": "🍋 Set Ácido",
        },
        "desc": {
            "uk": "Гозе, Томатний Гозе, Крік — 3 пляшки",
            "ru": "Гозе, Томатный Гозе, Крик — 3 бутылки",
            "en": "Gose, Tomato Gose, Kriek — 3 bottles",
            "es": "Gose, Tomate Gose, Kriek — 3 botellas",
        },
        "beers": [14, 15, 29],
        "discount_pct": 20,
    },
    {
        "id": "set_ipa",
        "name": {
            "uk": "🌿 IPA сет",
            "ru": "🌿 IPA сет",
            "en": "🌿 IPA Set",
            "es": "🌿 Set IPA",
        },
        "desc": {
            "uk": "Усі IPA — хмільовий рай!",
            "ru": "Все IPA — хмелевой рай!",
            "en": "All IPAs — hop heaven!",
            "es": "Todas las IPAs — ¡paraíso lupulado!",
        },
        "beers": [4, 5, 12, 16, 19, 20, 26, 27],
        "discount_pct": 20,
    },
    {
        "id": "set_dark",
        "name": {
            "uk": "🖤 Темний сет",
            "ru": "🖤 Тёмный сет",
            "en": "🖤 Dark Set",
            "es": "🖤 Set Oscuro",
        },
        "desc": {
            "uk": "Стаути, Раухбір — для цінителів темного",
            "ru": "Стауты, Раухбир — для ценителей тёмного",
            "en": "Stouts, Rauchbier — for dark beer lovers",
            "es": "Stouts, Rauchbier — para amantes de la oscura",
        },
        "beers": [8, 17, 21, 23, 24, 25, 30],
        "discount_pct": 20,
    },
    {
        "id": "set_strong",
        "name": {
            "uk": "💪 Міцний сет",
            "ru": "💪 Крепкий сет",
            "en": "💪 Strong Set",
            "es": "💪 Set Fuerte",
        },
        "desc": {
            "uk": "10%+ — Tripel, Wheatwine, Barleywine, Imperial Stout",
            "ru": "10%+ — Tripel, Wheatwine, Barleywine, Imperial Stout",
            "en": "10%+ — Tripel, Wheatwine, Barleywine, Imperial Stout",
            "es": "10%+ — Tripel, Wheatwine, Barleywine, Imperial Stout",
        },
        "beers": [11, 17, 22, 23, 28, 30],
        "discount_pct": 20,
    },
    {
        "id": "set_belgian",
        "name": {
            "uk": "🇧🇪 Бельгійський сет",
            "ru": "🇧🇪 Бельгийский сет",
            "en": "🇧🇪 Belgian Set",
            "es": "🇧🇪 Set Belga",
        },
        "desc": {
            "uk": "Wheat, Dubbel, Tripel, Kriek — класика Бельгії",
            "ru": "Wheat, Dubbel, Tripel, Kriek — классика Бельгии",
            "en": "Wheat, Dubbel, Tripel, Kriek — Belgian classics",
            "es": "Wheat, Dubbel, Tripel, Kriek — clásicos belgas",
        },
        "beers": [2, 10, 11, 29],
        "discount_pct": 20,
    },
]

# ═══════════════════════════════════════════════════════════════
# ПЕРЕКЛАДИ
# ═══════════════════════════════════════════════════════════════

T = {
    "choose_lang": "🌍 Обери мову / Выбери язык / Choose language / Elige idioma",

    "welcome": {
        "uk": (
            "🍺 *Привіт, {name}!*\n\n"
            "Ласкаво просимо до *Mountain Brew* — крафтова пивоварня в горах Коста Бланки 🏔🇺🇦\n\n"
            "Мін. замовлення: *{min_bottles} пляшок*\n"
            "Доставка: *€{delivery:.0f}* (Валенсія · Аліканте · Торрев'єха)\n\n"
            "Тисни 👇"
        ),
        "ru": (
            "🍺 *Привет, {name}!*\n\n"
            "Добро пожаловать в *Mountain Brew* — крафтовая пивоварня в горах Коста Бланки 🏔🇺🇦\n\n"
            "Мин. заказ: *{min_bottles} бутылок*\n"
            "Доставка: *€{delivery:.0f}* (Валенсия · Аликанте · Торревьеха)\n\n"
            "Жми 👇"
        ),
        "en": (
            "🍺 *Hey, {name}!*\n\n"
            "Welcome to *Mountain Brew* — craft brewery in the Costa Blanca mountains 🏔🇺🇦\n\n"
            "Min. order: *{min_bottles} bottles*\n"
            "Delivery: *€{delivery:.0f}* (Valencia · Alicante · Torrevieja)\n\n"
            "Tap below 👇"
        ),
        "es": (
            "🍺 *¡Hola, {name}!*\n\n"
            "Bienvenido a *Mountain Brew* — cervecería artesanal en las montañas de la Costa Blanca 🏔🇺🇦\n\n"
            "Pedido mín.: *{min_bottles} botellas*\n"
            "Envío: *€{delivery:.0f}* (Valencia · Alicante · Torrevieja)\n\n"
            "Pulsa abajo 👇"
        ),
    },

    "btn_menu":     {"uk": "🍻 Меню пива",       "ru": "🍻 Меню пива",       "en": "🍻 Beer Menu",        "es": "🍻 Menú de Cervezas"},
    "btn_sets":     {"uk": "🎁 Сети зі знижкою",  "ru": "🎁 Сеты со скидкой",  "en": "🎁 Discount Sets",    "es": "🎁 Sets con Descuento"},
    "btn_about":    {"uk": "ℹ️ Про нас",          "ru": "ℹ️ О нас",            "en": "ℹ️ About Us",         "es": "ℹ️ Sobre Nosotros"},
    "btn_cart":     {"uk": "🛒 Кошик",            "ru": "🛒 Корзина",          "en": "🛒 Cart",             "es": "🛒 Carrito"},
    "btn_add_more": {"uk": "➕ Додати ще",        "ru": "➕ Добавить ещё",      "en": "➕ Add More",         "es": "➕ Añadir Más"},
    "btn_clear":    {"uk": "🗑 Очистити",         "ru": "🗑 Очистить",         "en": "🗑 Clear Cart",       "es": "🗑 Vaciar"},
    "btn_checkout": {"uk": "✅ Оформити",         "ru": "✅ Оформить",         "en": "✅ Checkout",         "es": "✅ Pedir"},
    "btn_back":     {"uk": "« Назад",             "ru": "« Назад",             "en": "« Back",              "es": "« Volver"},
    "btn_confirm":  {"uk": "✅ Підтвердити",      "ru": "✅ Подтвердить",      "en": "✅ Confirm",          "es": "✅ Confirmar"},
    "btn_cancel":   {"uk": "❌ Скасувати",        "ru": "❌ Отменить",         "en": "❌ Cancel",           "es": "❌ Cancelar"},
    "btn_new":      {"uk": "🍻 Нове замовлення",  "ru": "🍻 Новый заказ",      "en": "🍻 New Order",        "es": "🍻 Nuevo Pedido"},
    "btn_lang":     {"uk": "🌍 Мова",             "ru": "🌍 Язык",             "en": "🌍 Language",         "es": "🌍 Idioma"},

    "choose_beer": {
        "uk": "🍺 *Обери сорт:*\n🔴 = знижка",
        "ru": "🍺 *Выбери сорт:*\n🔴 = скидка",
        "en": "🍺 *Choose a beer:*\n🔴 = sale",
        "es": "🍺 *Elige cerveza:*\n🔴 = oferta",
    },
    "in_cart": {
        "uk": "_(у кошику: {n} пл.)_",
        "ru": "_(в корзине: {n} бут.)_",
        "en": "_(in cart: {n} btl.)_",
        "es": "_(en carrito: {n} bot.)_",
    },
    "how_many": {
        "uk": "Скільки пляшок?",
        "ru": "Сколько бутылок?",
        "en": "How many bottles?",
        "es": "¿Cuántas botellas?",
    },
    "added": {
        "uk": "✅ Додано: #{num} {name} × {qty} шт.",
        "ru": "✅ Добавлено: #{num} {name} × {qty} шт.",
        "en": "✅ Added: #{num} {name} × {qty}",
        "es": "✅ Añadido: #{num} {name} × {qty}",
    },
    "cart_empty": {
        "uk": "🛒 Кошик порожній",
        "ru": "🛒 Корзина пуста",
        "en": "🛒 Cart is empty",
        "es": "🛒 Carrito vacío",
    },
    "cart_title": {
        "uk": "🛒 *Твій кошик:*\n",
        "ru": "🛒 *Твоя корзина:*\n",
        "en": "🛒 *Your cart:*\n",
        "es": "🛒 *Tu carrito:*\n",
    },
    "bottles":  {"uk": "📦 Пляшок: {n}",       "ru": "📦 Бутылок: {n}",       "en": "📦 Bottles: {n}",       "es": "📦 Botellas: {n}"},
    "subtotal": {"uk": "💰 За пиво: €{s:.2f}",  "ru": "💰 За пиво: €{s:.2f}",  "en": "💰 Beer: €{s:.2f}",     "es": "💰 Cerveza: €{s:.2f}"},
    "delivery": {"uk": "🚚 Доставка: €{d:.2f}", "ru": "🚚 Доставка: €{d:.2f}", "en": "🚚 Delivery: €{d:.2f}", "es": "🚚 Envío: €{d:.2f}"},
    "total":    {"uk": "*💶 Разом: €{t:.2f}*",   "ru": "*💶 Итого: €{t:.2f}*",   "en": "*💶 Total: €{t:.2f}*",   "es": "*💶 Total: €{t:.2f}*"},
    "saved":    {"uk": "💚 Знижка: −€{s:.2f}",  "ru": "💚 Скидка: −€{s:.2f}",  "en": "💚 Saved: −€{s:.2f}",   "es": "💚 Ahorro: −€{s:.2f}"},

    "min_warn": {
        "uk": "⚠️ Мін. {min} пл. (зараз {now})",
        "ru": "⚠️ Мин. {min} бут. (сейчас {now})",
        "en": "⚠️ Min. {min} btl. (now {now})",
        "es": "⚠️ Mín. {min} bot. (ahora {now})",
    },

    "ask_address": {
        "uk": "📍 *Куди доставити?*\n\nНапиши адресу або надішли геолокацію 👇",
        "ru": "📍 *Куда доставить?*\n\nНапиши адрес или отправь геолокацию 👇",
        "en": "📍 *Delivery address?*\n\nType your address or share location 👇",
        "es": "📍 *¿Dirección de entrega?*\n\nEscribe la dirección o comparte ubicación 👇",
    },
    "btn_location": {
        "uk": "📍 Надіслати геолокацію",
        "ru": "📍 Отправить геолокацию",
        "en": "📍 Share Location",
        "es": "📍 Enviar Ubicación",
    },
    "address_ok": {
        "uk": "✅ Адреса прийнята!",
        "ru": "✅ Адрес принят!",
        "en": "✅ Address received!",
        "es": "✅ ¡Dirección recibida!",
    },

    "ask_time": {
        "uk": "🕐 *Коли зручно прийняти доставку?*\n\nОбери слот або напиши свій час:",
        "ru": "🕐 *Когда удобно принять доставку?*\n\nВыбери слот или напиши своё время:",
        "en": "🕐 *Preferred delivery time?*\n\nPick a slot or type your time:",
        "es": "🕐 *¿Hora de entrega preferida?*\n\nElige un horario o escribe tu hora:",
    },

    "review_order": {
        "uk": "📋 *Перевір замовлення:*\n\n",
        "ru": "📋 *Проверь заказ:*\n\n",
        "en": "📋 *Review your order:*\n\n",
        "es": "📋 *Revisa tu pedido:*\n\n",
    },
    "address_label": {"uk": "📍 Адреса", "ru": "📍 Адрес",  "en": "📍 Address",   "es": "📍 Dirección"},
    "time_label":    {"uk": "🕐 Час",    "ru": "🕐 Время",  "en": "🕐 Time",      "es": "🕐 Hora"},
    "confirm_q": {
        "uk": "\n\n*Все вірно?* 👇",
        "ru": "\n\n*Всё верно?* 👇",
        "en": "\n\n*All correct?* 👇",
        "es": "\n\n*¿Todo correcto?* 👇",
    },

    "order_done": {
        "uk": "🎉 *Дякуємо! Замовлення прийнято!*\n\nМи зв'яжемось для підтвердження.\nПитання — пиши сюди ✌️\n\nНове замовлення → /start",
        "ru": "🎉 *Спасибо! Заказ принят!*\n\nМы свяжемся для подтверждения.\nВопросы — пиши сюда ✌️\n\nНовый заказ → /start",
        "en": "🎉 *Thank you! Order received!*\n\nWe'll contact you to confirm.\nQuestions — message us here ✌️\n\nNew order → /start",
        "es": "🎉 *¡Gracias! ¡Pedido recibido!*\n\nNos pondremos en contacto para confirmar.\n¿Preguntas? Escríbenos aquí ✌️\n\nNuevo pedido → /start",
    },
    "order_cancelled": {
        "uk": "❌ Замовлення скасовано.",
        "ru": "❌ Заказ отменён.",
        "en": "❌ Order cancelled.",
        "es": "❌ Pedido cancelado.",
    },
    "cart_cleared": {
        "uk": "🗑 Кошик очищено.",
        "ru": "🗑 Корзина очищена.",
        "en": "🗑 Cart cleared.",
        "es": "🗑 Carrito vaciado.",
    },

    "about": {
        "uk": (
            "🏔 *Mountain Brew*\n\n"
            "Крафтова пивоварня в горах за Бенідормом (Селья).\n"
            "Варимо пиво з українською душею під іспанським сонцем ☀️🇺🇦\n\n"
            "📍 Доставка: Валенсія · Аліканте · Торрев'єха\n"
            "📱 Питання → напиши нам у особисті"
        ),
        "ru": (
            "🏔 *Mountain Brew*\n\n"
            "Крафтовая пивоварня в горах за Бенидормом (Селья).\n"
            "Варим пиво с украинской душой под испанским солнцем ☀️🇺🇦\n\n"
            "📍 Доставка: Валенсия · Аликанте · Торревьеха\n"
            "📱 Вопросы → напиши нам в личку"
        ),
        "en": (
            "🏔 *Mountain Brew*\n\n"
            "Craft brewery in the mountains behind Benidorm (Sella).\n"
            "Brewing with a Ukrainian soul under the Spanish sun ☀️🇺🇦\n\n"
            "📍 Delivery: Valencia · Alicante · Torrevieja\n"
            "📱 Questions → DM us"
        ),
        "es": (
            "🏔 *Mountain Brew*\n\n"
            "Cervecería artesanal en las montañas detrás de Benidorm (Sella).\n"
            "Cerveza con alma ucraniana bajo el sol español ☀️🇺🇦\n\n"
            "📍 Envío: Valencia · Alicante · Torrevieja\n"
            "📱 ¿Preguntas? Escríbenos por privado"
        ),
    },

    "sets_title": {
        "uk": "🎁 *Сети зі знижкою:*\n\nОбери набір — отримай знижку!",
        "ru": "🎁 *Сеты со скидкой:*\n\nВыбери набор — получи скидку!",
        "en": "🎁 *Discount Sets:*\n\nPick a set — get a discount!",
        "es": "🎁 *Sets con Descuento:*\n\nElige un set — ¡consigue descuento!",
    },
    "set_detail": {
        "uk": "📦 *{name}*\n\n{desc}\n\n🏷 Знижка: *{pct}%*\n💰 Ціна: *€{set_price:.2f}* (замість €{full_price:.2f})\n📦 Пляшок: {count}",
        "ru": "📦 *{name}*\n\n{desc}\n\n🏷 Скидка: *{pct}%*\n💰 Цена: *€{set_price:.2f}* (вместо €{full_price:.2f})\n📦 Бутылок: {count}",
        "en": "📦 *{name}*\n\n{desc}\n\n🏷 Discount: *{pct}%*\n💰 Price: *€{set_price:.2f}* (was €{full_price:.2f})\n📦 Bottles: {count}",
        "es": "📦 *{name}*\n\n{desc}\n\n🏷 Descuento: *{pct}%*\n💰 Precio: *€{set_price:.2f}* (antes €{full_price:.2f})\n📦 Botellas: {count}",
    },
    "btn_add_set": {
        "uk": "🛒 Додати сет у кошик",
        "ru": "🛒 Добавить сет в корзину",
        "en": "🛒 Add set to cart",
        "es": "🛒 Añadir set al carrito",
    },
    "set_added": {
        "uk": "✅ Сет додано у кошик!",
        "ru": "✅ Сет добавлен в корзину!",
        "en": "✅ Set added to cart!",
        "es": "✅ ¡Set añadido al carrito!",
    },
}


# ═══════════════════════════════════════════════════════════════
# ▲▲▲  КІНЕЦЬ НАЛАШТУВАНЬ  ▲▲▲
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Стани розмови
(
    STATE_LANG,
    STATE_MENU,
    STATE_CHOOSE_BEER,
    STATE_CHOOSE_QTY,
    STATE_CART,
    STATE_SETS,
    STATE_SET_DETAIL,
    STATE_ADDRESS,
    STATE_TIME,
    STATE_CONFIRM,
) = range(10)

# Сховище користувачів (в пам'яті)
user_data_store: dict = {}


def get_user(user_id: int) -> dict:
    if user_id not in user_data_store:
        user_data_store[user_id] = {
            "lang": None, "items": [], "address": "", "time": "", "location": None
        }
    return user_data_store[user_id]


def tr(key: str, user_id: int) -> str:
    """Отримати переклад для користувача."""
    lang = get_user(user_id).get("lang", "uk")
    val = T.get(key, key)
    if isinstance(val, dict):
        return val.get(lang, val.get("uk", str(val)))
    return str(val)


def get_beer(num: int):
    return next((b for b in BEER_MENU if b[0] == num), None)


def beer_price(beer_tuple) -> float:
    """Актуальна ціна (зі знижкою якщо є)."""
    _, _, _, price, discount, _ = beer_tuple
    return discount if discount is not None else price


def beer_available():
    return [b for b in BEER_MENU if b[5]]


def get_set_beers(s: dict) -> list:
    if s["beers"] == "ALL_AVAILABLE":
        return beer_available()
    return [b for b in (get_beer(n) for n in s["beers"]) if b and b[5]]


def calc_set_price(s: dict) -> tuple:
    """(повна ціна без знижок, ціна сету, кількість пляшок)."""
    beers = get_set_beers(s)
    full = sum(beer_price(b) for b in beers)
    discounted = round(full * (1 - s["discount_pct"] / 100), 2)
    return full, discounted, len(beers)


def count_bottles(items: list) -> int:
    """Підрахунок пляшок з урахуванням сетів."""
    total = 0
    for i in items:
        if i.get("is_set"):
            total += i.get("bottles", 1)
        else:
            total += i["qty"]
    return total


def format_cart(user_id: int) -> str:
    ud = get_user(user_id)
    items = ud["items"]
    if not items:
        return tr("cart_empty", user_id)

    lines = [tr("cart_title", user_id)]
    total = 0.0
    total_bottles = 0

    for item in items:
        sub = item["price"] * item["qty"]
        total += sub
        if item.get("is_set"):
            btl = item.get("bottles", 1)
            total_bottles += btl
            lines.append(f"  🎁 {item['name']} ({btl} 🍺) = €{sub:.2f}")
        else:
            total_bottles += item["qty"]
            lines.append(f"  #{item['num']} {item['name']} — {item['qty']} × €{item['price']:.2f} = €{sub:.2f}")

    lines.append("")
    lines.append(tr("bottles", user_id).format(n=total_bottles))
    lines.append(tr("subtotal", user_id).format(s=total))
    lines.append(tr("delivery", user_id).format(d=DELIVERY_COST))
    lines.append(tr("total", user_id).format(t=total + DELIVERY_COST))
    return "\n".join(lines)


# ──────────────────────────────────────
# /start → вибір мови
# ──────────────────────────────────────

async def cmd_start(update: Update, context) -> int:
    uid = update.effective_user.id
    user_data_store.pop(uid, None)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk")],
        [InlineKeyboardButton("🇷🇺 Русский",    callback_data="lang_ru")],
        [InlineKeyboardButton("🇬🇧 English",    callback_data="lang_en")],
        [InlineKeyboardButton("🇪🇸 Español",    callback_data="lang_es")],
    ])
    await update.message.reply_text(T["choose_lang"], reply_markup=keyboard)
    return STATE_LANG


# ──────────────────────────────────────
# Головне меню
# ──────────────────────────────────────

async def show_main_menu(target, uid: int, name: str, edit: bool = False):
    text = tr("welcome", uid).format(name=name, min_bottles=MIN_ORDER_BOTTLES, delivery=DELIVERY_COST)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(tr("btn_menu", uid),  callback_data="show_menu")],
        [InlineKeyboardButton(tr("btn_sets", uid),  callback_data="show_sets")],
        [InlineKeyboardButton(tr("btn_cart", uid),  callback_data="view_cart")],
        [InlineKeyboardButton(tr("btn_about", uid), callback_data="about")],
        [InlineKeyboardButton(tr("btn_lang", uid),  callback_data="change_lang")],
    ])
    if edit:
        await target.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await target.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


# ──────────────────────────────────────
# Меню пива (10 на сторінку)
# ──────────────────────────────────────

PAGE_SIZE = 10


def menu_keyboard(uid: int, page: int = 0) -> InlineKeyboardMarkup:
    beers = beer_available()
    total_pages = max(1, (len(beers) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    chunk = beers[start:start + PAGE_SIZE]

    buttons = []
    for num, name, abv, price, discount, _ in chunk:
        if discount is not None:
            label = f"🔴 #{num} {name} ({abv}) €{discount:.2f}"
        else:
            label = f"#{num} {name} ({abv}) €{price:.2f}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"beer_{num}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"page_{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(tr("btn_cart", uid), callback_data="view_cart")])
    buttons.append([InlineKeyboardButton(tr("btn_back", uid), callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def cart_keyboard(uid: int) -> InlineKeyboardMarkup:
    ud = get_user(uid)
    buttons = []
    if ud["items"]:
        buttons.append([InlineKeyboardButton(tr("btn_add_more", uid), callback_data="show_menu")])
        buttons.append([InlineKeyboardButton(tr("btn_sets", uid),     callback_data="show_sets")])
        buttons.append([InlineKeyboardButton(tr("btn_clear", uid),    callback_data="clear_cart")])
        total_bottles = count_bottles(ud["items"])
        if total_bottles >= MIN_ORDER_BOTTLES:
            buttons.append([InlineKeyboardButton(tr("btn_checkout", uid), callback_data="checkout")])
        else:
            buttons.append([InlineKeyboardButton(
                tr("min_warn", uid).format(min=MIN_ORDER_BOTTLES, now=total_bottles),
                callback_data="show_menu"
            )])
    else:
        buttons.append([InlineKeyboardButton(tr("btn_menu", uid), callback_data="show_menu")])
    buttons.append([InlineKeyboardButton(tr("btn_back", uid), callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


# ──────────────────────────────────────
# Callback handler
# ──────────────────────────────────────

async def callback_handler(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id
    ud = get_user(uid)
    name = query.from_user.first_name or ""

    # --- Мова ---
    if data.startswith("lang_"):
        ud["lang"] = data.split("_")[1]
        await show_main_menu(query, uid, name, edit=True)
        return STATE_MENU

    if data == "change_lang":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk")],
            [InlineKeyboardButton("🇷🇺 Русский",    callback_data="lang_ru")],
            [InlineKeyboardButton("🇬🇧 English",    callback_data="lang_en")],
            [InlineKeyboardButton("🇪🇸 Español",    callback_data="lang_es")],
        ])
        await query.edit_message_text(T["choose_lang"], reply_markup=keyboard)
        return STATE_LANG

    if data == "noop":
        return STATE_CHOOSE_BEER

    # --- Головне меню ---
    if data == "main_menu":
        await show_main_menu(query, uid, name, edit=True)
        return STATE_MENU

    # --- Про нас ---
    if data == "about":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(tr("btn_menu", uid), callback_data="show_menu")],
            [InlineKeyboardButton(tr("btn_back", uid), callback_data="main_menu")],
        ])
        await query.edit_message_text(tr("about", uid), reply_markup=keyboard, parse_mode="Markdown")
        return STATE_MENU

    # --- Меню пива ---
    if data == "show_menu":
        page = 0
        context.user_data["menu_page"] = page
        total_btl = count_bottles(ud["items"])
        header = tr("choose_beer", uid)
        if total_btl > 0:
            header += "\n" + tr("in_cart", uid).format(n=total_btl)
        await query.edit_message_text(header, reply_markup=menu_keyboard(uid, page), parse_mode="Markdown")
        return STATE_CHOOSE_BEER

    if data.startswith("page_"):
        page = int(data.split("_")[1])
        context.user_data["menu_page"] = page
        total_btl = count_bottles(ud["items"])
        header = tr("choose_beer", uid)
        if total_btl > 0:
            header += "\n" + tr("in_cart", uid).format(n=total_btl)
        await query.edit_message_text(header, reply_markup=menu_keyboard(uid, page), parse_mode="Markdown")
        return STATE_CHOOSE_BEER

    # --- Вибрали пиво ---
    if data.startswith("beer_"):
        beer_num = int(data.split("_")[1])
        beer = get_beer(beer_num)
        if not beer or not beer[5]:
            return STATE_MENU
        context.user_data["selected_beer"] = beer
        num, bname, abv, price, discount, _ = beer
        actual = discount if discount is not None else price

        text = f"🍺 *#{num} {bname}*\n{abv} · €{actual:.2f}"
        if discount is not None:
            text += f"  ~(€{price:.2f})~"
        text += f"\n\n{tr('how_many', uid)}"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("1", callback_data="qty_1"),
                InlineKeyboardButton("2", callback_data="qty_2"),
                InlineKeyboardButton("3", callback_data="qty_3"),
            ],
            [
                InlineKeyboardButton("4", callback_data="qty_4"),
                InlineKeyboardButton("6", callback_data="qty_6"),
                InlineKeyboardButton("12", callback_data="qty_12"),
            ],
            [InlineKeyboardButton(tr("btn_back", uid), callback_data="show_menu")],
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return STATE_CHOOSE_QTY

    # --- Кількість ---
    if data.startswith("qty_"):
        qty = int(data.split("_")[1])
        beer = context.user_data.get("selected_beer")
        if not beer:
            return STATE_MENU
        num, bname, abv, price, discount, _ = beer
        actual = discount if discount is not None else price

        existing = next((i for i in ud["items"] if i.get("num") == num and not i.get("is_set")), None)
        if existing:
            existing["qty"] += qty
        else:
            ud["items"].append({"num": num, "name": bname, "price": actual, "qty": qty})

        text = tr("added", uid).format(num=num, name=bname, qty=qty) + "\n\n" + format_cart(uid)
        await query.edit_message_text(text, reply_markup=cart_keyboard(uid), parse_mode="Markdown")
        return STATE_CART

    # --- Кошик ---
    if data == "view_cart":
        text = format_cart(uid)
        await query.edit_message_text(text, reply_markup=cart_keyboard(uid), parse_mode="Markdown")
        return STATE_CART

    if data == "clear_cart":
        ud["items"] = []
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(tr("btn_menu", uid), callback_data="show_menu")],
        ])
        await query.edit_message_text(tr("cart_cleared", uid), reply_markup=keyboard)
        return STATE_MENU

    # ──────────────────────────────────
    # СЕТИ
    # ──────────────────────────────────

    if data == "show_sets":
        lang = ud.get("lang", "uk")
        buttons = []
        for s in BEER_SETS:
            beers_in_set = get_set_beers(s)
            if len(beers_in_set) < 2:
                continue
            full, disc, count = calc_set_price(s)
            label = f"{s['name'][lang]} ({count} 🍺 −{s['discount_pct']}%)"
            buttons.append([InlineKeyboardButton(label, callback_data=f"setinfo_{s['id']}")])
        buttons.append([InlineKeyboardButton(tr("btn_back", uid), callback_data="main_menu")])
        await query.edit_message_text(
            tr("sets_title", uid), reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown"
        )
        return STATE_SETS

    if data.startswith("setinfo_"):
        set_id = data.replace("setinfo_", "")
        s = next((x for x in BEER_SETS if x["id"] == set_id), None)
        if not s:
            return STATE_SETS
        lang = ud.get("lang", "uk")
        full, disc, count = calc_set_price(s)
        beers_in = get_set_beers(s)
        beer_list = "\n".join(f"  #{b[0]} {b[1]}" for b in beers_in)
        text = tr("set_detail", uid).format(
            name=s["name"][lang], desc=s["desc"][lang],
            pct=s["discount_pct"], set_price=disc, full_price=full, count=count
        )
        text += f"\n\n{beer_list}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(tr("btn_add_set", uid), callback_data=f"addset_{set_id}")],
            [InlineKeyboardButton(tr("btn_back", uid), callback_data="show_sets")],
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return STATE_SET_DETAIL

    if data.startswith("addset_"):
        set_id = data.replace("addset_", "")
        s = next((x for x in BEER_SETS if x["id"] == set_id), None)
        if not s:
            return STATE_SETS
        lang = ud.get("lang", "uk")
        full, disc, count = calc_set_price(s)
        beers_in = get_set_beers(s)

        ud["items"].append({
            "is_set": True,
            "set_id": set_id,
            "name": s["name"][lang],
            "price": disc,
            "qty": 1,
            "num": 0,
            "bottles": count,
            "beers_detail": [f"#{b[0]} {b[1]}" for b in beers_in],
        })

        text = tr("set_added", uid) + "\n\n" + format_cart(uid)
        await query.edit_message_text(text, reply_markup=cart_keyboard(uid), parse_mode="Markdown")
        return STATE_CART

    # ──────────────────────────────────
    # ОФОРМЛЕННЯ
    # ──────────────────────────────────

    if data == "checkout":
        text = tr("ask_address", uid)
        loc_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(tr("btn_location", uid), request_location=True)]],
            resize_keyboard=True, one_time_keyboard=True,
        )
        await query.message.reply_text(text, reply_markup=loc_keyboard, parse_mode="Markdown")
        return STATE_ADDRESS

    if data.startswith("time_"):
        time_choice = data.replace("time_", "").replace("_", ":")
        ud["time"] = time_choice
        return await show_confirmation(query.message, uid, edit=False)

    if data == "confirm_order":
        return await send_order(query, context)

    if data == "cancel_order":
        user_data_store.pop(uid, None)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(tr("btn_new", uid), callback_data="show_menu")]
        ])
        await query.edit_message_text(tr("order_cancelled", uid), reply_markup=keyboard)
        return STATE_MENU

    return STATE_MENU


# ──────────────────────────────────────
# Адреса
# ──────────────────────────────────────

async def handle_address_text(update: Update, context) -> int:
    uid = update.effective_user.id
    ud = get_user(uid)
    ud["address"] = update.message.text
    ud["location"] = None
    await update.message.reply_text(tr("address_ok", uid), reply_markup=ReplyKeyboardRemove())
    return await ask_time(update, uid)


async def handle_address_location(update: Update, context) -> int:
    uid = update.effective_user.id
    ud = get_user(uid)
    loc = update.message.location
    ud["location"] = {"lat": loc.latitude, "lon": loc.longitude}
    ud["address"] = f"📍 {loc.latitude:.5f}, {loc.longitude:.5f}"
    await update.message.reply_text(tr("address_ok", uid), reply_markup=ReplyKeyboardRemove())
    return await ask_time(update, uid)


async def ask_time(update: Update, uid: int) -> int:
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("10:00–13:00", callback_data="time_10_00-13_00"),
            InlineKeyboardButton("13:00–16:00", callback_data="time_13_00-16_00"),
        ],
        [
            InlineKeyboardButton("16:00–19:00", callback_data="time_16_00-19_00"),
            InlineKeyboardButton("19:00–21:00", callback_data="time_19_00-21_00"),
        ],
    ])
    await update.message.reply_text(tr("ask_time", uid), reply_markup=keyboard, parse_mode="Markdown")
    return STATE_TIME


async def handle_time_text(update: Update, context) -> int:
    uid = update.effective_user.id
    ud = get_user(uid)
    ud["time"] = update.message.text
    return await show_confirmation(update.message, uid, edit=False)


# ──────────────────────────────────────
# Підтвердження
# ──────────────────────────────────────

async def show_confirmation(message, uid: int, edit: bool = False) -> int:
    ud = get_user(uid)
    text = tr("review_order", uid)
    text += format_cart(uid)
    text += f"\n\n{tr('address_label', uid)}: {ud['address']}"
    text += f"\n{tr('time_label', uid)}: {ud['time']}"
    text += tr("confirm_q", uid)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(tr("btn_confirm", uid), callback_data="confirm_order")],
        [InlineKeyboardButton(tr("btn_cancel", uid),  callback_data="cancel_order")],
    ])
    if edit:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    return STATE_CONFIRM


# ──────────────────────────────────────
# Відправка замовлення адміну
# ──────────────────────────────────────

def send_to_google_sheets(data: dict):
    """Відправити замовлення в Google Таблицю через Apps Script."""
    if not GOOGLE_SCRIPT_URL:
        return  # URL не налаштований — пропускаємо
    try:
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            GOOGLE_SCRIPT_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode("utf-8"))
        logger.info(f"Google Sheets: {result}")
    except Exception as e:
        logger.error(f"Google Sheets error: {e}")


async def send_order(query, context) -> int:
    user = query.from_user
    uid = user.id
    ud = get_user(uid)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    total = sum(i["price"] * i["qty"] for i in ud["items"])
    total_bottles = count_bottles(ud["items"])

    # Текст замовлення для деталей
    details_parts = []
    for item in ud["items"]:
        if item.get("is_set"):
            details_parts.append(f"🎁 {item['name']} ({item.get('bottles', '?')} бут.) — €{item['price']:.2f}")
        else:
            details_parts.append(f"#{item['num']} {item['name']} × {item['qty']} = €{item['price'] * item['qty']:.2f}")
    order_details = "; ".join(details_parts)

    order_text = (
        f"🆕 *НОВЕ ЗАМОВЛЕННЯ*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 {user.first_name} {user.last_name or ''}\n"
        f"📱 @{user.username or 'no username'}\n"
        f"🆔 `{uid}`\n"
        f"🗓 {now}\n"
        f"🌍 {ud.get('lang', '?').upper()}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    for item in ud["items"]:
        if item.get("is_set"):
            order_text += f"  🎁 {item['name']} ({item.get('bottles', '?')} бут.) — €{item['price']:.2f}\n"
            for bd in item.get("beers_detail", []):
                order_text += f"     {bd}\n"
        else:
            sub = item["price"] * item["qty"]
            order_text += f"  #{item['num']} {item['name']} — {item['qty']} × €{item['price']:.2f} = €{sub:.2f}\n"

    order_text += (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 Пляшок: {total_bottles}\n"
        f"💰 Пиво: €{total:.2f}\n"
        f"🚚 Доставка: €{DELIVERY_COST:.2f}\n"
        f"*💶 РАЗОМ: €{total + DELIVERY_COST:.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📍 {ud['address']}\n"
        f"🕐 {ud['time']}\n"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=order_text, parse_mode="Markdown")
        if ud.get("location"):
            await context.bot.send_location(
                chat_id=ADMIN_CHAT_ID,
                latitude=ud["location"]["lat"],
                longitude=ud["location"]["lon"],
            )
    except Exception as e:
        logger.error(f"Error sending order to admin: {e}")

    # ── Відправка в Google Таблицю ──
    geo = ud.get("location")
    send_to_google_sheets({
        "client_name": f"{user.first_name} {user.last_name or ''}".strip(),
        "client_username": f"@{user.username}" if user.username else "",
        "client_id": str(uid),
        "lang": ud.get("lang", "?"),
        "order_details": order_details,
        "total_bottles": total_bottles,
        "beer_total": round(total, 2),
        "delivery_cost": DELIVERY_COST,
        "grand_total": round(total + DELIVERY_COST, 2),
        "address": ud["address"],
        "geo_lat": geo["lat"] if geo else None,
        "geo_lon": geo["lon"] if geo else None,
        "delivery_time": ud["time"],
    })

    await query.edit_message_text(tr("order_done", uid), parse_mode="Markdown")
    user_data_store.pop(uid, None)
    return ConversationHandler.END


async def cmd_cancel(update: Update, context) -> int:
    uid = update.effective_user.id
    user_data_store.pop(uid, None)
    await update.message.reply_text("❌", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ──────────────────────────────────────
# Запуск
# ──────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            STATE_LANG:        [CallbackQueryHandler(callback_handler)],
            STATE_MENU:        [CallbackQueryHandler(callback_handler)],
            STATE_CHOOSE_BEER: [CallbackQueryHandler(callback_handler)],
            STATE_CHOOSE_QTY:  [CallbackQueryHandler(callback_handler)],
            STATE_CART:        [CallbackQueryHandler(callback_handler)],
            STATE_SETS:        [CallbackQueryHandler(callback_handler)],
            STATE_SET_DETAIL:  [CallbackQueryHandler(callback_handler)],
            STATE_ADDRESS: [
                MessageHandler(filters.LOCATION, handle_address_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_address_text),
            ],
            STATE_TIME: [
                CallbackQueryHandler(callback_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_text),
            ],
            STATE_CONFIRM: [CallbackQueryHandler(callback_handler)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CommandHandler("start", cmd_start),
        ],
    )

    app.add_handler(conv)
    print("🍺 Mountain Brew Bot v2.0 запущено!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
