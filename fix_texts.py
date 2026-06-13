#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اسکریپت اصلاح متن‌های فارسی در handlers.py"""

import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# لیست اصلاحات: (متن اشتباه, متن درست)
fixes = [
    # میهمان -> مهمان
    ('میهمان', 'مهمان'),
    # اخطار -> هشدار (در متن اتمام انبار)
    ('اخطار اتمام انبار', 'هشدار اتمام انبار'),
    # تشکیل صف -> ورود به صف
    ('تشکیل صف', 'ورود به صف'),
    # مانیتوریNگ -> پایش
    ('مانیتورینگ', 'پایش'),
    # اورجینال -> اصلی
    ('اورجینال', 'اصلی'),
    # اسرع -> اسرع (تغییر نداره، عربی رایج هست)
    # ارقام فارسی در پرانتز V2ray
    ('سرویس‌های پرسرعت V2ray', 'سرویس‌های پرسرعت V2ray'),
    # نیم‌فاصله‌های گمشده
    ('زیرمجموعه گیری', 'زیرمجموعه‌گیری'),
    ('فیلد ها', 'فیلدها'),
]

for wrong, correct in fixes:
    if wrong in content:
        content = content.replace(wrong, correct)
        print(f"✅ اصلاح شد: '{wrong}' -> '{correct}'")
    else:
        print(f"⚠️ پیدا نشد: '{wrong}'")

# اضافه کردن ایموجی به متن دو کاربره در نمایش صف‌های انتظار
old_line = "◽ صف اکسپرس تک کاربره: <code>{len(config.WAITING_QUEUE['ex_1user'])}</code> نفر | دو کاربره: <code>{len(config.WAITING_QUEUE['ex_2user'])}</code> نفر"
new_line = "◽ صف اکسپرس تک‌کاربره: <code>{len(config.WAITING_QUEUE['ex_1user'])}</code> نفر | صف اکسپرس دوکاربره: <code>{len(config.WAITING_QUEUE['ex_2user'])}</code> نفر"
if old_line in content:
    content = content.replace(old_line, new_line)
    print(f"✅ ایموجی اشتباه صف اکسپرس اصلاح شد")

with open('handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n🔋 فایل handlers.py با موفقیت بروزرسانی شد!")
