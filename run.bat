@echo off
TITLE Uruchamianie Neuralka...

:: 1. Przejdz do folderu projektu (zabezpieczenie, gdybys odpalal skrot z pulpitu)
cd /d "C:\Users\szymo\Desktop\STUDIA AI_ML\MojeNotatki"

:: 2. Aktywuj srodowisko wirtualne
call venv\Scripts\activate

:: 3. Uruchom aplikacje
echo Uruchamianie aplikacji...
python main.py

:: 4. Jesli wystapi blad, zatrzymaj okno, zebys mogl przeczytac komunikat
if %errorlevel% neq 0 pause