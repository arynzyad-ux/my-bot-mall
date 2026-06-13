# bot.py
import config
import handlers
import database
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)
from config import (
    TOKEN, ADMIN_ID, GET_AMOUNT, GET_RECEIPT,
    ADMIN_GET_USER, ADMIN_GET_BALANCE_CHNG, ADMIN_GET_DISCOUNT, ADMIN_GET_BROADCAST,
    ADMIN_GET_BLOCK_ID, ADMIN_GET_UNBLOCK_ID, ADMIN_CHOOSE_STOCK_TYPE, ADMIN_GET_STOCK_CONTENT,
    SUPPORT_MESSAGE
)

# فعال‌سازی لاگر سیستم جهت رهگیری دقیق خطاها
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
print("🔋 دیتابیس با موفقیت راه‌اندازی شد.", flush=True)

def main():
    # ساخت اپلیکیشن ربات تلگرام با توکن پیکربندی شده
    application = Application.builder().token(config.TOKEN).build()

    # 💳 پیاده‌سازی سیستم کانورزیشن شارژ کیف پول کاربر
    wallet_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handlers.request_amount, pattern="^charge_wallet$")],
        states={
            GET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.process_amount)],
            GET_RECEIPT: [
                CallbackQueryHandler(handlers.request_receipt, pattern="^send_receipt$"),
                MessageHandler(filters.PHOTO, handlers.process_receipt)
            ]
        },
        fallbacks=[CallbackQueryHandler(handlers.cancel_and_main, pattern="^back_to_main$")],
        per_message=False
    )

    # ⚙️ پیاده‌سازی سیستم کانورزیشن پنل مدیریت فوق پیشرفته
    admin_conv = ConversationHandler(
        entry_points=[
            CommandHandler("admin", handlers.admin_menu_cmd),
            CallbackQueryHandler(handlers.admin_wallet_start, pattern="^admin_manage_wallet$"),
            CallbackQueryHandler(handlers.admin_discount_start, pattern="^admin_set_discount$"),
            CallbackQueryHandler(handlers.admin_block_start, pattern="^admin_block_user$"),
            CallbackQueryHandler(handlers.admin_unblock_start, pattern="^admin_unblock_user$"),
            CallbackQueryHandler(handlers.admin_broadcast_start, pattern="^admin_broadcast$"),
            CallbackQueryHandler(handlers.admin_add_stock_menu, pattern="^admin_add_stock_menu$")
        ],
        states={
            ADMIN_GET_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.admin_wallet_user_received)],
            ADMIN_GET_BALANCE_CHNG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.admin_wallet_amount_received)],
            ADMIN_GET_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.admin_discount_received)],
            ADMIN_GET_BLOCK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.admin_block_received)],
            ADMIN_GET_UNBLOCK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.admin_unblock_received)],
            ADMIN_GET_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.admin_broadcast_received)],
            ADMIN_CHOOSE_STOCK_TYPE: [CallbackQueryHandler(handlers.admin_add_stock_select, pattern="^add_stock_")],
            ADMIN_GET_STOCK_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.admin_add_stock_save)]
        },
        fallbacks=[CallbackQueryHandler(handlers.admin_cancel, pattern="^admin_back$")],
        per_message=False
    )

    # 🆘 پیاده‌سازی سیستم پشتیبانی (کاربر پیام میدهد → ادمین ریپلای میزند)
    support_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handlers.support_start, pattern="^support$")],
        states={
            SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.support_received)]
        },
        fallbacks=[CallbackQueryHandler(handlers.cancel_and_main, pattern="^back_to_main$")],
        per_message=False
    )

    # ثبت تمامی کامندها و هندلرهای مدیریت دکمه‌های اصلی سیستم
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(admin_conv)
    application.add_handler(wallet_conv)
    application.add_handler(support_conv)

    # ثبت دکمه‌های تصمیم‌گیری مدیریت فیش‌ها
    application.add_handler(CallbackQueryHandler(handlers.handle_admin_decision, pattern="^verify_"))
    application.add_handler(CallbackQueryHandler(handlers.admin_view_stock, pattern="^admin_view_stock$"))
    application.add_handler(CallbackQueryHandler(handlers.admin_full_report, pattern="^admin_full_report$"))

    # ⚡ هندلر مرکزی و همه‌کاره برای دکمه‌های منوی کاربری (جهت حل قطعی مشکل هدایت دکمه‌ها)
    application.add_handler(CallbackQueryHandler(handlers.handle_main_menu_callbacks))

    # 💬 هندلر ریپلای ادمین برای پشتیبانی
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY & filters.UpdateType.MESSAGE, handlers.handle_admin_reply))

    # روشن کردن پولینگ و اجرای ربات
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
