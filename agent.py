import os
import json
from pathlib import Path

import pandas as pd
import joblib
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_api_key = os.environ.get("OPENROUTER_API_KEY")
if not _api_key:
    raise RuntimeError(
        "متغیر محیطی OPENROUTER_API_KEY تنظیم نشده است. "
        "آن را در فایل .env یا در Streamlit Secrets قرار دهید."
    )

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=_api_key,
)

FEATURE_WEIGHTS = {
    "پارکینگ": 3,
    "انباری": 2,
    "دارای بالکن": 1,
    "نورگیر": 1,
    "نوساز": 2,
    "بازسازی‌شده": 1,
    "سند تک‌برگ": 2,
    "دارای اتاق مستر": 2,
    "دارای کولر گازی": 1,
    "دارای پکیج": 1,
    "دارای استخر": 3,
    "دارای جکوزی": 2,
    "دارای روف‌گاردن": 2,
    "دارای نگهبانی": 2,
    "دارای سرایدار": 1,
}

OPTIONAL_FEATURE_KEY_MAP = {
    "پارکینگ": "پارکینگ",
    "انباری": "انباری",
    "بالکن": "دارای بالکن",
    "نورگیر": "نورگیر",
    "نوساز": "نوساز",
    "بازسازی‌شده": "بازسازی‌شده",
    "سند تک‌برگ": "سند تک‌برگ",
    "اتاق مستر": "دارای اتاق مستر",
    "کولر گازی": "دارای کولر گازی",
    "پکیج": "دارای پکیج",
    "استخر": "دارای استخر",
    "جکوزی": "دارای جکوزی",
    "روف‌گاردن": "دارای روف‌گاردن",
    "نگهبانی": "دارای نگهبانی",
    "سرایدار": "دارای سرایدار",
}

REQUIRED_FIELDS = [
    "متراژ",
    "ناحیه",
    "سال ساخت",
    "تعداد اتاق خواب",
    "طبقه ملک",
    "طبقه کل ساختمان",
]

BASE_YEAR = 1405

MODEL_FEATURES_ORDER = [
    "متراژ",
    "ناحیه",
    "سال ساخت",
    "سن ساختمان",
    "تعداد اتاق خواب",
    "طبقه ملک",
    "طبقه کل ساختمان",
    "Property Feature Score",
]

PRICE_ROUNDING_STEP = 10_000_000


def calculate_property_feature_score(property_data: dict, has_elevator: int, floor: int) -> float:
    score = 0
    for user_key, weight_key in OPTIONAL_FEATURE_KEY_MAP.items():
        raw_value = property_data.get(user_key)
        value = 1 if raw_value else 0
        score += value * FEATURE_WEIGHTS[weight_key]

    floor_for_elevator = max(floor, 0)
    elevator_value = has_elevator * floor_for_elevator
    elevator_penalty = (1 - has_elevator) * floor_for_elevator
    score += elevator_value
    score -= elevator_penalty

    return max(score, 0)


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "house_price_model.pkl"
best_gb_model = joblib.load(MODEL_PATH)


def check_missing_required(property_data: dict) -> list:
    missing = []
    for field in REQUIRED_FIELDS:
        value = property_data.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def predict_price(property_data: dict) -> dict:
    missing = check_missing_required(property_data)
    if missing:
        return {
            "status": "missing_required_fields",
            "missing_fields": missing,
        }

    متراژ = property_data["متراژ"]
    ناحیه = property_data["ناحیه"]
    سال_ساخت = property_data["سال ساخت"]
    تعداد_اتاق_خواب = property_data["تعداد اتاق خواب"]
    طبقه_ملک = property_data["طبقه ملک"]
    طبقه_کل_ساختمان = property_data["طبقه کل ساختمان"]

    سن_ساختمان = BASE_YEAR - سال_ساخت
    has_elevator = 1 if property_data.get("آسانسور") else 0
    score = calculate_property_feature_score(property_data, has_elevator, طبقه_ملک)

    model_input = pd.DataFrame([{
        "متراژ": متراژ,
        "ناحیه": ناحیه,
        "سال ساخت": سال_ساخت,
        "سن ساختمان": سن_ساختمان,
        "تعداد اتاق خواب": تعداد_اتاق_خواب,
        "طبقه ملک": طبقه_ملک,
        "طبقه کل ساختمان": طبقه_کل_ساختمان,
        "Property Feature Score": score,
    }])[MODEL_FEATURES_ORDER]

    predicted_price = best_gb_model.predict(model_input)[0]

    predicted_price = round(predicted_price / PRICE_ROUNDING_STEP) * PRICE_ROUNDING_STEP

    missing_optional = [
        k for k in list(OPTIONAL_FEATURE_KEY_MAP.keys()) + ["آسانسور"]
        if property_data.get(k) is None
    ]

    return {
        "status": "ok",
        "predicted_price": float(predicted_price),
        "property_feature_score": float(score),
        "building_age": int(سن_ساختمان),
        "missing_optional_info": missing_optional,
    }


tools = [
    {
        "type": "function",
        "function": {
            "name": "predict_price",
            "description": (
                "پیش‌بینی قیمت یک ملک با استفاده از مدل قیمت‌گذاری آموزش‌دیده. "
                "این تابع را فقط زمانی صدا بزن که تمام Featureهای حیاتی "
                "(متراژ، ناحیه، سال ساخت، تعداد اتاق خواب، طبقه ملک، طبقه کل ساختمان) "
                "را از کاربر داری. اگر هرکدام را نداری، اول از کاربر بپرس و تابع را صدا نزن."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "متراژ": {"type": "number", "description": "متراژ ملک به متر مربع"},
                    "ناحیه": {"type": "string", "description": "نام محله یا ناحیه ملک"},
                    "سال ساخت": {"type": "integer", "description": "سال ساخت ملک (شمسی)"},
                    "تعداد اتاق خواب": {"type": "integer"},
                    "طبقه ملک": {"type": "integer", "description": "طبقه‌ای که واحد در آن قرار دارد"},
                    "طبقه کل ساختمان": {"type": "integer", "description": "تعداد کل طبقات ساختمان"},
                    "پارکینگ": {"type": "boolean"},
                    "انباری": {"type": "boolean"},
                    "بالکن": {"type": "boolean"},
                    "نورگیر": {"type": "boolean"},
                    "نوساز": {"type": "boolean"},
                    "بازسازی‌شده": {"type": "boolean"},
                    "سند تک‌برگ": {"type": "boolean"},
                    "اتاق مستر": {"type": "boolean"},
                    "کولر گازی": {"type": "boolean"},
                    "پکیج": {"type": "boolean"},
                    "استخر": {"type": "boolean"},
                    "جکوزی": {"type": "boolean"},
                    "روف‌گاردن": {"type": "boolean"},
                    "نگهبانی": {"type": "boolean"},
                    "سرایدار": {"type": "boolean"},
                    "آسانسور": {"type": "boolean"},
                },
                "required": [
                    "متراژ",
                    "ناحیه",
                    "سال ساخت",
                    "تعداد اتاق خواب",
                    "طبقه ملک",
                    "طبقه کل ساختمان",
                ],
            },
        },
    }
]

system_prompt = {
    "role": "system",
    "content": (
        "تو یک مشاور املاک هوشمند هستی و باید کاملاً طبیعی و روان به زبان فارسی با کاربر صحبت کنی. "
        "هدف اصلی تو کمک به کاربر برای برآورد قیمت یک ملک است. "
        "قانون بسیار مهم: "
        "هرگز قیمت ملک را خودت حدس نزن و هیچ عددی برای قیمت تولید نکن. "
        "قیمت فقط و فقط باید از نتیجه تابع predict_price گرفته شود. "
        "همچنین هرگز Property Feature Score را خودت محاسبه نکن. "
        "تو فقط باید اطلاعات خام ملک را از صحبت کاربر استخراج کنی و به تابع predict_price بدهی. "
        "اطلاعات حیاتی موردنیاز برای پیش‌بینی عبارت‌اند از: "
        "متراژ، ناحیه، سال ساخت، تعداد اتاق خواب، طبقه ملک و طبقه کل ساختمان. "
        "اگر هرکدام از این اطلاعات وجود نداشت، خالی بود یا مشخص نبود، "
        "نباید تابع predict_price را صدا بزنی. "
        "در عوض، به‌صورت طبیعی و کوتاه از کاربر بخواه اطلاعات ناقص را وارد کند. "
        "اطلاعات مربوط به امکانات ملک مانند پارکینگ، انباری، بالکن، نورگیر، "
        "نوساز، بازسازی‌شده، سند تک‌برگ، اتاق مستر، کولر گازی، پکیج، "
        "استخر، جکوزی، روف‌گاردن، نگهبانی، سرایدار و آسانسور اطلاعات اختیاری هستند. "
        "اگر بعضی از این اطلاعات توسط کاربر ارائه نشدند، "
        "نباید از کاربر برای آن‌ها سؤال اجباری بپرسی و نباید پیش‌بینی را متوقف کنی. "
        "تابع predict_price خودش اطلاعات ناقص اختیاری را مدیریت می‌کند. "
        "بعد از اجرای موفق predict_price، مقدار predicted_price موجود در نتیجه تابع را "
        "به‌عنوان قیمت پیش‌بینی‌شده اعلام کن. "
        "این عدد از قبل به نزدیک‌ترین ۱۰ میلیون تومان گرد شده است؛ "
        "آن را دقیقاً همان‌طور که هست (بدون هیچ رقم اعشار یا جزئیات اضافه) به کاربر اعلام کن، "
        "دوباره گردش نکن و عدد دیگری جایگزینش نکن. "
        "اگر missing_optional_info در نتیجه تابع وجود داشت و خالی نبود، "
        "بعد از اعلام قیمت، به‌صورت کوتاه و طبیعی به کاربر اطلاع بده که "
        "اگر اطلاعات بیشتری درباره امکانات ملک ارائه کند، برآورد می‌تواند دقیق‌تر شود. "
        "اگر missing_optional_info خالی بود، درباره اطلاعات ناقص اختیاری چیزی نگو. "
        "اطلاعاتی که کاربر درباره ملک می‌دهد را تغییر نده. "
        "نام محله، عدد متراژ، سال ساخت، تعداد اتاق‌ها و طبقات را دقیقاً همان‌طور که "
        "کاربر گفته حفظ کن و هنگام پاسخ دادن آن‌ها را حدس نزن یا تغییر نده. "
        "اگر نتیجه تابع شامل property_feature_score یا building_age بود، "
        "لازم نیست این مقادیر را به کاربر نشان بدهی مگر اینکه کاربر درباره آن‌ها سؤال کند. "
        "پاسخ نهایی باید کوتاه، واضح، حرفه‌ای و طبیعی باشد. "
        "هدف این است که کاربر احساس کند با یک مشاور املاک هوشمند صحبت می‌کند، "
        "نه اینکه یک گزارش فنی دریافت می‌کند."
    ),
}


def run_agent(user_message: str, history: list | None = None):
    """
    یک چرخه‌ی کامل: پیام کاربر -> LLM -> (در صورت نیاز) اجرای predict_price -> پاسخ نهایی.
    history: پیام‌های قبلی مکالمه (برای حفظ context بین چند نوبت).
    """
    messages = history[:] if history else [system_prompt]
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="openrouter/free",
        messages=messages,
        tools=tools,
    )

    message = response.choices[0].message
    messages.append(message)

    tool_calls = message.tool_calls or []
    for tool_call in tool_calls:
        if tool_call.function.name == "predict_price":
            args = json.loads(tool_call.function.arguments)
            result = predict_price(args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    if tool_calls:
        final_response = client.chat.completions.create(
            model="openrouter/free",
            messages=messages,
        )
        final_message = final_response.choices[0].message
        messages.append(final_message)
        return final_message.content, messages

    return message.content, messages


if __name__ == "__main__":
    answer, history = run_agent(
        "یک آپارتمان 120 متری در عظیمیه، ساخت 1400، دو خواب، طبقه سوم از پنج طبقه، "
        "با پارکینگ و انباری دارم. قیمتش چقدر است؟"
    )
    print(answer)
