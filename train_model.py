"""
train_model.py - Haqiqiy OLX ma'lumotlari asosida AI modelini o'qitish.
"""
import pandas as pd
import numpy as np
import os
import joblib
import json
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import OrdinalEncoder
from sklearn.metrics import mean_absolute_error, r2_score

DATA_FILE  = "data/cars_data.csv"
MODEL_FILE = "model.pkl"
META_FILE  = "model_meta.json"

def remove_price_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Har bir brend+model juftligi uchun narx outlierlarni olib tashlash.
    IQR usuli ishlatiladi.
    """
    cleaned_parts = []
    for (brand, model), group in df.groupby(['Brand', 'Model']):
        if len(group) < 3:
            # Kam namuna bo'lsa, faqat global filterdan o'tkazilgan narxni qabul qil
            cleaned_parts.append(group)
            continue
        Q1 = group['Price_USD'].quantile(0.15)
        Q3 = group['Price_USD'].quantile(0.85)
        IQR = Q3 - Q1
        lower = Q1 - 2.0 * IQR
        upper = Q3 + 2.0 * IQR
        filtered = group[(group['Price_USD'] >= lower) & (group['Price_USD'] <= upper)]
        if len(filtered) == 0:
            cleaned_parts.append(group)
        else:
            cleaned_parts.append(filtered)
    return pd.concat(cleaned_parts, ignore_index=True)

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # Narx
    df = df[df['Price_USD'].notna()].copy()
    df['Price_USD'] = pd.to_numeric(df['Price_USD'], errors='coerce')
    df.dropna(subset=['Price_USD'], inplace=True)
    # Juda arzon yoki juda qimmat narxlarni bekor qilish
    df = df[(df['Price_USD'] >= 500) & (df['Price_USD'] <= 500000)]

    # Yil
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    df = df[(df['Year'] >= 1990) & (df['Year'] <= 2026)]

    # Probeg
    df['Mileage_km'] = pd.to_numeric(df['Mileage_km'], errors='coerce')
    df['Mileage_km'] = df['Mileage_km'].fillna(df['Mileage_km'].median())
    df['Mileage_km'] = df['Mileage_km'].clip(0, 800000)

    # Kategoriyalarni tozalash
    def clean_cat(col):
        df[col] = df[col].astype(str).str.strip().str.replace("'", "").str.lower()
        df[col] = df[col].replace({"noma lum": "unknown", "nan": "unknown"})
    for c in ['Brand', 'Model', 'Transmission', 'Color', 'FuelType']:
        clean_cat(c)

    # Brand va Modelni capitalize
    df['Brand'] = df['Brand'].str.capitalize()
    df['Model'] = df['Model'].str.capitalize()

    # Per-brand-model outlierlarni olib tashlash
    df = remove_price_outliers(df)

    return df

def train_main():
    if not os.path.exists(DATA_FILE):
        print(f"[XATO] {DATA_FILE} topilmadi. python scraper.py ni avval ishga tushiring.")
        return

    df_raw = pd.read_csv(DATA_FILE)
    print(f"CSV da jami: {len(df_raw)} qator")

    df = clean_data(df_raw)
    print(f"Tozalangandan keyin: {len(df)} qator")

    if len(df) < 20:
        print("[XATO] Model o'qitish uchun yetarli ma'lumot yo'q (kamida 20 qator kerak).")
        return

    # ── Feature Engineering ──
    cat_cols = ['Brand', 'Model', 'Transmission', 'Color', 'FuelType']
    num_cols = ['Year', 'Mileage_km']

    feature_cols = num_cols + cat_cols
    X = df[feature_cols].copy()
    y = df['Price_USD']

    # OrdinalEncoder
    encoder = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
    X[cat_cols] = encoder.fit_transform(X[cat_cols].astype(str))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        min_samples_leaf=3,
        random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae   = mean_absolute_error(y_test, preds)
    r2    = r2_score(y_test, preds)
    print(f"\n[OK] Model o'qitildi!")
    print(f"   MAE (O'rtacha xatolik): ${mae:,.0f}")
    print(f"   R2 Score:               {r2:.3f}")

    # Saqlash
    joblib.dump(model,   MODEL_FILE)
    joblib.dump(encoder, "encoder.pkl")

    # ── Per-brand-model meta (rang, karobka, yoqilg'i) ──
    brand_model_map = {}
    brand_model_options = {}  # { "Brand||Model": { colors, transmissions, fuels } }

    for brand, brand_group in df.groupby('Brand'):
        brand_model_map[brand] = sorted(brand_group['Model'].unique().tolist())
        for model_name, model_group in brand_group.groupby('Model'):
            key = f"{brand}||{model_name}"
            brand_model_options[key] = {
                "colors":        sorted(model_group['Color'].unique().tolist()),
                "transmissions": sorted(model_group['Transmission'].unique().tolist()),
                "fuels":         sorted(model_group['FuelType'].unique().tolist()),
            }

    meta = {
        "cat_cols":           cat_cols,
        "num_cols":           num_cols,
        "feature_cols":       feature_cols,
        "brands_models":      brand_model_map,
        "brand_model_options": brand_model_options,
        "colors":             sorted(df['Color'].unique().tolist()),
        "transmissions":      sorted(df['Transmission'].unique().tolist()),
        "fuels":              sorted(df['FuelType'].unique().tolist()),
        "year_min":           int(df['Year'].min()),
        "year_max":           int(df['Year'].max()),
        "mileage_max":        int(df['Mileage_km'].max()) if not pd.isna(df['Mileage_km'].max()) else 500000,
        "total_records":      len(df),
        "mae":                round(float(mae), 2),
        "r2":                 round(float(r2), 4),
    }
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"   Jami brendlar: {len(brand_model_map)}")
    print(f"   Saqlandi: {MODEL_FILE}, encoder.pkl, {META_FILE}")

if __name__ == "__main__":
    train_main()
