@echo off
cd /d "%~dp0"
echo Installing required packages...
pip install flask numpy requests scikit-learn pyflakes pytest chromadb
set /p GEMINI_API_KEY=Paste your Gemini API key and press Enter: 
set GEMINI_MODEL=gemini-flash-latest
start "" http://127.0.0.1:5001
python app.py
pause