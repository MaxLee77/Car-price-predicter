@echo off
echo Eski ma'lumotlar o'chirilmoqda...
del /f /q data\cars_data.csv 2>nul
del /f /q model.pkl encoder.pkl model_meta.json 2>nul

echo.
echo Scraper ishga tushmoqda (~30-40 daqiqa kutish kerak)...
echo Har bir yozilgan elon ekranda ko'rinadi.
call venv\Scripts\activate.bat
python scraper.py

echo.
echo AI modeli o'qitilmoqda...
python train_model.py

echo.
echo Dastur ishga tushmoqda...
start http://localhost:8501
streamlit run app.py
pause
