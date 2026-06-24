@echo off
chcp 65001 >nul
cd /d "%~dp0"
python remove_red_marks.py --ghost-mode --ghost-desaturate --output-dir output_weak --mask-dir masks_weak --preview-dir previews_weak
pause
