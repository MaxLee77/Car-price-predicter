# 🚗 Mashina Narxini Aniqlash (Car Price Predictor AI)

Ushbu loyiha OLX.uz saytidan real avtomobil e'lonlarini skreyp qilib, yig'ilgan ma'lumotlar asosida mashina narxini bashorat qiladi.

## 🚀 Loyiha tarkibi
- `app.py` - Streamlit veb-ilovasi.
- `scraper.py` - OLX.uz dan ma'lumot yig'uvchi skript.
- `train_model.py` - AI modelini o'qitish skripti.
- `model.pkl` - O'qitilgan Random Forest modeli.
- `encoder.pkl` - Kategoriyalarni kodlovchi fayl.
- `model_meta.json` - UI uchun zarur bo'lgan metadata.

## 🛠 O'rnatish
Loyiha kutubxonalarini o'rnatish uchun:
```bash
pip install -r requirements.txt
```

## 📊 Ma'lumotlarni yangilash
Yangi ma'lumotlarni yig'ish va modelni qayta o'qitish uchun:
```bash
python scraper.py
python train_model.py
```

## 💻 Ilovani ishga tushirish
```bash
streamlit run app.py
```
