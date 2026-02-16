# bot.py - ربات فروشگاهی کامل تلگرام با aiogram 3.x (به‌روز 2026)
# فیکس 100% با تمام فیچرها: منو اصلی، محصولات با عکس، سبد خرید، پرداخت زرین‌پال، سفارش‌ها، پنل ادمین
# پیش‌نیازها: pip install aiogram requests python-dotenv --upgrade
# فایل .env بساز (کنار bot.py) با محتوای:
# BOT_TOKEN=your_token
# ADMIN_ID=your_id
# MERCHANT_ID=your_zarinpal_merchant

import asyncio
import logging
import os
import requests
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from dotenv import load_dotenv
from aiogram.utils.keyboard import InlineKeyboardBuilder
from collections import Counter 
# لاگینگ برای دیباگ (اختیاری)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# لود متغیرها از .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
MERCHANT_ID = os.getenv("MERCHANT_ID")

if not BOT_TOKEN or not MERCHANT_ID:
    raise ValueError("BOT_TOKEN یا MERCHANT_ID پیدا نشد! فایل .env را چک کن.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# لیست محصولات (اینجا محصولات خودت رو بذار - لینک عکس‌ها رو جایگزین کن)
products = [
    {
        "id": 1,
        "name": "ساق دست ضد UV خورشید",
        "price": 95000,
        "desc": "ضد اشعه UV، خنک‌کننده، مناسب رانندگی و فعالیت‌های خارجی",
        "photo": "https://t.me/royalpaw2/7"  # لینک واقعی عکس رو عوض کن
    },
    {
        "id": 2,
        "name": "قوزبند طبی اصلاح قوز کمر",
        "price": 450000,
        "desc": "اصلاح افتادگی شانه، کاهش درد گردن و کمر، قابل تنظیم",
        "photo": "https://t.me/royalpaw2/8"
    },
    {
        "id": 3,
        "name": "ماساژور قاعدگی حرارتی و تسکین درد",
        "price": 650000,
        "desc": "گرمایش موضعی + ویبره، تسکین درد قاعدگی و عضلات شکم",
        "photo": "https://t.me/your_channel/3"
    },
    {
        "id": 4,
        "name": "ماساژور همه کاره رفع خستگی بدن و عضلات",
        "price": 850000,
        "desc": "چند حالته، مناسب کمر، پا، شانه، افزایش گردش خون",
        "photo": "https://t.me/your_channel/4"
    },
    {
        "id": 5,
        "name": "کیسه آب گرم طرح فانتزی",
        "price": 120000,
        "desc": "طرح‌های کیوت، بدون نشتی، تسکین درد عضلانی",
        "photo": "https://t.me/royalpaw2/9"
    },

    
    # اگر محصول بیشتری داری اضافه کن
]

# سبد خرید: {user_id: [product_ids]} - برای تعداد، لیست رو تکراری استفاده کن
carts = {}

# سفارش‌ها: {order_id: dict}
orders = {}
order_counter = 1

# تابع منو اصلی (دکمه‌های پایین چت)
def get_main_menu(is_admin=False):
    buttons = [
        [KeyboardButton(text="محصولات"), KeyboardButton(text="سبد خرید")],
        [KeyboardButton(text="سفارش‌های من"), KeyboardButton(text="پشتیبانی")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="پنل ادمین")])
    
    markup = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
    )
    return markup

# هندلر /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    is_admin = message.from_user.id == ADMIN_ID
    await message.answer(
        "سلام! به فروشگاه لوازم آرایشی و سلامتی خوش آمدید 💄✨",
        reply_markup=get_main_menu(is_admin),
    )

# دکمه "محصولات" - نمایش لیست با دکمه inline
@dp.message(F.text == "محصولات")
async def show_products(message: types.Message):
    inline_kb = [
        [InlineKeyboardButton(
            text=f"{p['name']} – {p['price']:,} تومان",
            callback_data=f"view_{p['id']}"
        )]
        for p in products
    ]

    markup = InlineKeyboardMarkup(inline_keyboard=inline_kb)

    await message.answer("انتخاب محصول:", reply_markup=markup)
@dp.callback_query(F.data.startswith("view_"))
async def view_product(callback: types.CallbackQuery):
    try:
        prod_id = int(callback.data.split("_")[1])
        prod = next((p for p in products if p["id"] == prod_id), None)
        
        if not prod:
            await callback.answer("محصول یافت نشد!", show_alert=True)
            return

        # روش درست ساخت کیبورد در aiogram 3
        builder = InlineKeyboardBuilder()
        builder.button(
            text="➕ افزودن به سبد خرید",
            callback_data=f"add_{prod_id}"
        )
        builder.adjust(1)  # یک دکمه در هر ردیف

        markup = builder.as_markup()

        await callback.message.answer_photo(
            photo=prod["photo"],
            caption=f"<b>{prod['name']}</b>\n\n{prod['desc']}\n\nقیمت: {prod['price']:,} تومان",
            parse_mode="HTML",
            reply_markup=markup
        )
        
        await callback.answer()  # حذف لودینگ ساعت شنی

    except Exception as e:
        logger.error(f"خطا در نمایش محصول: {e}")
        await callback.answer("خطایی رخ داد", show_alert=True)
# callback برای افزودن به سبد
@dp.callback_query(F.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    try:
        prod_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        if user_id not in carts:
            carts[user_id] = []
        
        carts[user_id].append(prod_id)
        
        prod_name = next((p["name"] for p in products if p["id"] == prod_id), "نامشخص")
        await callback.answer(
            text=f"{prod_name} به سبد اضافه شد ✓",
            show_alert=False
        )
    except Exception as e:
        logger.error(f"خطا در افزودن به سبد: {e}")
        await callback.answer("خطا!", show_alert=True)

# دکمه "سبد خرید" - نمایش اقلام و مجموع + دکمه پرداخت
@dp.message(F.text == "سبد خرید")
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    
    print(f"کاربر {user_id} سبد خرید را باز کرد")  # برای دیباگ
    
    if user_id not in carts or len(carts[user_id]) == 0:
        await message.answer("سبد خرید شما خالی است 😔")
        return
    
    # شمارش تعداد هر محصول
    from collections import Counter
    counts = Counter(carts[user_id])
    
    text = "<b>🛒 سبد خرید شما:</b>\n\n"
    total = 0
    
    for pid, qty in counts.items():
        prod = next((p for p in products if p["id"] == pid), None)
        if prod:
            subtotal = prod["price"] * qty
            total += subtotal
            text += f"• {prod['name']} × {qty} = {subtotal:,} تومان\n"
        else:
            text += f"• محصول ID {pid} (نامشخص) × {qty}\n"
    
    text += f"\n━━━━━━━━━━━━━━━\n"
    text += f"<b>مجموع: {total:,} تومان</b>"
    
    # ساخت کیبورد درست در aiogram 3
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    if total > 0:
        builder.button(text="💳 پرداخت سفارش", callback_data="pay")
    
    builder.adjust(1)  # یک دکمه در ردیف
    
    markup = builder.as_markup()
    
    await message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=markup
    )
# callback برای پرداخت (زرین‌پال)
@dp.callback_query(F.data == "pay")
async def start_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in carts or not carts[user_id]:
        await callback.answer("سبد خرید خالی است!", show_alert=True)
        return
    
    # محاسبه مجموع (به ریال برای زرین‌پال)
    total_toman = 0
    for pid in carts[user_id]:
        prod = next((p for p in products if p["id"] == pid), None)
        if prod:
            total_toman += prod["price"]
    
    if total_toman <= 0:
        await callback.answer("مبلغ معتبر نیست!", show_alert=True)
        return
    
    total_rial = total_toman * 10  # زرین‌پال به ریال کار می‌کند
    
    # درخواست پرداخت
    payload = {
        "merchant_id": MERCHANT_ID,
        "amount": total_rial,
        "callback_url": f"https://t.me/{(await bot.get_me()).username}?start=pay_success",  # یا لینک دلخواه
        "description": f"پرداخت سفارش از ربات تلگرام - کاربر {user_id}",
        "metadata": {"telegram_user_id": str(user_id)}
    }
    
    try:
        response = requests.post(
            "https://api.zarinpal.com/pg/v4/payment/request.json",
            json=payload,
            timeout=15
        )
        response.raise_for_status()  # اگر 4xx یا 5xx بود ارور بده
        
        result = response.json()
        logger.info(f"پاسخ زرین‌پال: {result}")
        
        data = result.get("data", {})
        errors = result.get("errors", {})
        
        if data.get("code") in (100, 101):
            authority = data["authority"]
            pay_url = f"https://www.zarinpal.com/pg/StartPay/{authority}"
            
            # ذخیره سفارش قبل از ارسال لینک
            global order_counter
            order_id = order_counter
            orders[order_id] = {
                "user_id": user_id,
                "products": carts[user_id][:],
                "total_toman": total_toman,
                "authority": authority,
                "status": "pending",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            order_counter += 1
            
            # لینک پرداخت با deep link به ربات
            deep_link = f"https://t.me/{(await bot.get_me()).username}?start=verify_{authority}"
            
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("پرداخت آنلاین", url=pay_url)
            )
            
            await callback.message.answer(
                f"مجموع: {total_toman:,} تومان\n\n"
                f"برای پرداخت کلیک کنید:\n"
                f"بعد از پرداخت موفق، می‌توانید با دستور /verify_{authority} وضعیت را چک کنید.",
                reply_markup=markup,
                disable_web_page_preview=True
            )
            
            # سبد را بعد از ایجاد پرداخت خالی کن
            del carts[user_id]
            
        else:
            error_message = errors.get("message", "خطای نامشخص از زرین‌پال")
            await callback.message.answer(f"خطا در ایجاد درگاه پرداخت:\n{error_message}")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"خطا در ارتباط با زرین‌پال: {e}")
        await callback.message.answer("مشکلی در اتصال به درگاه پرداخت پیش آمد. بعداً امتحان کنید.")
    
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در پرداخت: {e}")
        await callback.message.answer("خطای سیستمی رخ داد. لطفاً بعداً امتحان کنید.")
    
    await callback.answer()
# دکمه "سفارش‌های من" - نمایش سفارش‌ها
@dp.message(F.text == "سفارش‌های من")
async def my_orders(message: types.Message):
    user_id = message.from_user.id
    user_orders = [
        f"سفارش #{oid}: {order['status']} - {order['total']:,} تومان - تاریخ: {order['date'][:10]}"
        for oid, order in orders.items()
        if order["user_id"] == user_id
    ]
    text = "\n".join(user_orders) or "شما سفارشی ندارید 😔"
    await message.answer(text)

# دکمه "پشتیبانی"
@dp.message(F.text == "پشتیبانی")
async def support(message: types.Message):
    await message.answer("برای پشتیبانی پیام خود را بنویسید یا به @meysamheq پیام بدهید.")

# ──────────────── پنل ادمین ────────────────

from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 همه سفارش‌ها", callback_data="admin_all_orders")
    builder.button(text="⏳ سفارش‌های در انتظار", callback_data="admin_pending_orders")
    builder.button(text="📊 آمار فروش", callback_data="admin_stats")
    builder.button(text="🔙 خروج از پنل", callback_data="admin_exit")
    builder.adjust(1)
    return builder.as_markup()


@dp.message(F.text == "پنل ادمین")
async def admin_panel_entry(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("شما ادمین نیستید! 🚫")
        return
    
    await message.answer(
        "🛠 **پنل مدیریت فروشگاه**\n\nچه کاری می‌خواهید انجام دهید؟",
        reply_markup=get_admin_menu()   # بدون آرگومان
    )


@dp.callback_query(F.data.startswith("admin_"))
async def admin_callback_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("دسترسی ندارید!", show_alert=True)
        return
    
    data = callback.data
    
    if data == "admin_all_orders":
        if not orders:
            await callback.message.edit_text("هیچ سفارشی ثبت نشده است.")
        else:
            text = "<b>📋 همه سفارش‌ها:</b>\n\n"
            for oid, order in sorted(orders.items(), reverse=True):
                text += f"سفارش #{oid} – کاربر {order['user_id']} – {order.get('total_toman', 0):,} تومان – {order.get('status', 'نامشخص')}\n"
            await callback.message.edit_text(text, parse_mode="HTML")
    
    elif data == "admin_pending_orders":
        pending = [o for o in orders.values() if o.get("status") == "pending"]
        if not pending:
            await callback.message.edit_text("سفارش در انتظار وجود ندارد.")
        else:
            text = "<b>⏳ سفارش‌های در انتظار:</b>\n\n"
            for o in pending:
                text += f"کاربر {o['user_id']} – {o.get('total_toman', 0):,} تومان\n"
            await callback.message.edit_text(text, parse_mode="HTML")
    
    elif data == "admin_stats":
        total_orders = len(orders)
        total_sales = sum(o.get("total_toman", 0) for o in orders.values())
        text = f"<b>📊 آمار</b>\n\nتعداد سفارش‌ها: {total_orders}\nمجموع فروش: {total_sales:,} تومان"
        await callback.message.edit_text(text, parse_mode="HTML")
    
    elif data == "admin_exit":
        await callback.message.delete()
        await callback.message.answer("از پنل خارج شدید.", reply_markup=get_main_menu())
    
    await callback.answer()

# تابع اصلی اجرا
async def main():
    logger.info("ربات شروع به کار کرد...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())