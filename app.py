import streamlit as st
import pandas as pd
import joblib
import json
import os

MODEL_FILE  = "model.pkl"
ENCODER_FILE = "encoder.pkl"
META_FILE   = "model_meta.json"

st.set_page_config(
    page_title="Mashina Narxini Aniqlash — AI",
        layout="centered",
)

# ── CSS ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.metric-box {
    background: linear-gradient(135deg,#1a1a2e,#16213e);
    border: 1px solid #0f3460;
    border-radius: 16px;
    padding: 28px;
    text-align: center;
    color: white;
}
.metric-box h1 { font-size: 3rem; margin: 0; color: #e94560; }
.metric-box p  { color: #aaa; margin: 4px 0 0; }
.stButton>button {
    width: 100%;
    background: linear-gradient(90deg,#e94560,#c2185b);
    color: white;
    font-weight: 700;
    border: none;
    padding: 14px;
    border-radius: 10px;
    font-size: 1.05rem;
    cursor: pointer;
}
.stButton>button:hover { opacity: .9; }
</style>
""", unsafe_allow_html=True)

st.title("Mashina Narxini Aniqlash (AI)")
st.caption("OLX.uz'dagi real elonlar bilan o'rgatilgan Sun'iy Intelekt")

# ── Model va meta yuklash ──
if not all(os.path.exists(f) for f in [MODEL_FILE, ENCODER_FILE, META_FILE]):
    st.error("Model topilmadi. Terminalda: `python scraper.py` → `python train_model.py`")
    st.stop()

@st.cache_resource
def load_model():
    return joblib.load(MODEL_FILE), joblib.load(ENCODER_FILE)

@st.cache_data
def load_meta():
    with open(META_FILE, encoding="utf-8") as f:
        return json.load(f)

model, encoder = load_model()
meta = load_meta()

brands_models       = meta["brands_models"]          # { "Chevrolet": ["Cobalt",...], ...}
brand_model_options = meta.get("brand_model_options", {})  # { "Chevrolet||Cobalt": {...} }
all_brands          = sorted(brands_models.keys())
all_colors          = [c.capitalize() for c in meta.get("colors", ["Oq","Qora","Sivoy"])]
all_transmissions   = [t.capitalize() for t in meta.get("transmissions", ["Avtomat","Mexanika"])]
all_fuels           = [f.capitalize() for f in meta.get("fuels", ["Benzin","Gaz","Elektr"])]
year_min            = meta.get("year_min", 1990)
year_max            = meta.get("year_max", 2026)
mileage_max         = meta.get("mileage_max", 500000)

st.markdown(f"""
<div style="display:flex;gap:12px;margin-bottom:18px">
  <div style="flex:1;background:#1e2a3a;border-radius:10px;padding:14px;text-align:center">
    <div style="font-size:1.6rem;font-weight:700;color:#e94560">{meta.get('total_records','?')}</div>
    <div style="color:#aaa;font-size:.8rem">Real elon</div>
  </div>
  <div style="flex:1;background:#1e2a3a;border-radius:10px;padding:14px;text-align:center">
    <div style="font-size:1.6rem;font-weight:700;color:#e94560">{len(all_brands)}</div>
    <div style="color:#aaa;font-size:.8rem">Brend</div>
  </div>
  <div style="flex:1;background:#1e2a3a;border-radius:10px;padding:14px;text-align:center">
    <div style="font-size:1.6rem;font-weight:700;color:#4caf50">R²={meta.get('r2','?')}</div>
    <div style="color:#aaa;font-size:.8rem">Model aniqligi</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Forma ──
col1, col2 = st.columns(2)

with col1:
    brand = st.selectbox("Mashina Brendi", all_brands)

# Brendga qarab modellar dinamik o'zgaradi
available_models_raw = brands_models.get(brand, ["Unknown"])
available_models = [m.capitalize() for m in available_models_raw]

with col2:
    car_model = st.selectbox("Modeli", available_models)

col3, col4 = st.columns(2)
with col3:
    year = st.slider("Ishlab chiqarilgan yili", year_min, year_max, 2020)
with col4:
    mileage = st.slider("Probeg (km)", 0, mileage_max, 50000, step=1000)

# ── Tanlangan brend+modelga mos rang, karobka, yoqilg'i ──
bm_key = f"{brand}||{car_model}"
bm_opts = brand_model_options.get(bm_key, {})

if bm_opts:
    avail_colors        = [c.capitalize() for c in bm_opts.get("colors", [])]        or all_colors
    avail_transmissions = [t.capitalize() for t in bm_opts.get("transmissions", [])] or all_transmissions
    avail_fuels         = [f.capitalize() for f in bm_opts.get("fuels", [])]         or all_fuels
else:
    avail_colors        = all_colors
    avail_transmissions = all_transmissions
    avail_fuels         = all_fuels

col5, col6, col7 = st.columns(3)
with col5:
    color = st.selectbox("Rang", avail_colors)
with col6:
    transmission = st.selectbox("Karobka", avail_transmissions)
with col7:
    fuel = st.selectbox("Yoqilg'i", avail_fuels)

st.markdown("")
predict_btn = st.button("Narxni taxmin qilish")

if predict_btn:
    cat_cols     = meta["cat_cols"]
    num_cols     = meta["num_cols"]
    feature_cols = meta["feature_cols"]

    # Encoder Brand va Model uchun capitalize, qolganlar lowercase ishlatiladi
    input_row = {
        "Year":         year,
        "Mileage_km":   mileage,
        "Brand":        brand,           # capitalize (e.g. "Chevrolet")
        "Model":        car_model,       # capitalize (e.g. "Cobalt")
        "Transmission": transmission.lower(),
        "Color":        color.lower(),
        "FuelType":     fuel.lower(),
    }
    df_in = pd.DataFrame([input_row])[feature_cols]
    df_in[cat_cols] = encoder.transform(df_in[cat_cols].astype(str))

    price = model.predict(df_in)[0]
    price_som = int(price * 12800)

    # Narx oraliqni hisoblash (±15%)
    low  = int(price * 0.85)
    high = int(price * 1.15)

    st.markdown(f"""
    <div class="metric-box">
      <p>Taxminiy bozor narxi</p>
      <h1>${price:,.0f}</h1>
      <p>≈ {price_som:,} so'm &nbsp;|&nbsp; Oraliq: ${low:,} – ${high:,}</p>
    </div>
    """, unsafe_allow_html=True)

    st.info("Bu narx mashinaning hozirgi holati, kraskasi va boshqa individual xususiyatlarini inobatga olmaydi.")
