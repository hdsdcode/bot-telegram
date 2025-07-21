@echo off
echo 🚀 Iniciando Bot Telegram Curriculo...

REM Carregar variáveis do arquivo .env
for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b

REM Executar o bot
python bot_curriculo.py
