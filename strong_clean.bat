@echo off
chcp 65001 >nul
cd /d "%~dp0"
python remove_red_marks.py --ghost-mode --ghost-near-red-px 18 --ghost-saturation-min 12 --ghost-red-strength 5 --ghost-lab-a-min 130 --ghost-expand-px 2 --ghost-radius 4 --ghost-passes 2 --output-dir output_strong --mask-dir masks_strong --preview-dir previews_strong
pause
