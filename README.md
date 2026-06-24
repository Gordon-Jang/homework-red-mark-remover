# 作业红色批改批量去除工具

一个本地 OpenCV 批处理小工具，用于检测作业纸照片里的红色/粉红色批改痕迹，并批量生成清理后的图片、检测蒙版和对比预览。

> 说明：本工具只适合整理、归档、视觉清理用途。不要用于伪造作业状态、成绩或其它误导性场景。

## 功能

- 批量处理 `jpg`、`jpeg`、`png`、`bmp`、`tif`、`tiff`、`webp`
- 支持中文路径和中文文件名
- 两种清理模式：
  - `弱清除.bat`：默认推荐，保留横线优先，先清除明显红笔，再淡化浅红残影
  - `强清除.bat`：清除更强，残影更少，但红笔压住横线的位置可能出现断线
- 输出三类文件：
  - 清理后图片
  - 红色检测蒙版
  - 三联预览：原图 | 检测区域 | 处理后

## 快速使用

1. 第一次使用先双击 `install_dependencies.bat` 安装依赖。
2. 把要处理的图片放入 `input_images` 文件夹。
3. 双击 `弱清除.bat` 或 `强清除.bat`。
4. 查看输出：
   - 弱清除结果：`output_weak`
   - 强清除结果：`output_strong`
   - 弱清除预览：`previews_weak`
   - 强清除预览：`previews_strong`
   - 检测蒙版：`masks_weak` / `masks_strong`

## 命令行使用

```powershell
python -m pip install -r requirements.txt
python remove_red_marks.py --ghost-mode --ghost-desaturate --output-dir output_weak --mask-dir masks_weak --preview-dir previews_weak
python remove_red_marks.py --ghost-mode --ghost-near-red-px 18 --ghost-saturation-min 12 --ghost-red-strength 5 --ghost-lab-a-min 130 --ghost-expand-px 2 --ghost-radius 4 --ghost-passes 2 --output-dir output_strong --mask-dir masks_strong --preview-dir previews_strong
```

只测试单张图片时，可以用文件名片段过滤：

```powershell
python remove_red_marks.py --only 621_7 --ghost-mode --ghost-desaturate --output-dir output_weak --mask-dir masks_weak --preview-dir previews_weak
```

## 目录说明

```text
input_images/     放原图，不上传到 GitHub
output_weak/      弱清除成品，不上传到 GitHub
output_strong/    强清除成品，不上传到 GitHub
previews_weak/    弱清除预览，不上传到 GitHub
previews_strong/  强清除预览，不上传到 GitHub
masks_weak/       弱清除蒙版，不上传到 GitHub
masks_strong/     强清除蒙版，不上传到 GitHub
remove_red_marks.py
弱清除.bat
强清除.bat
install_dependencies.bat
```

## 注意事项

- 自动修复无法完美恢复被红笔覆盖的黑色线条或文字。
- 如果弱清除仍有红色残影，可以试强清除。
- 如果强清除导致横线断裂，优先使用弱清除结果，再对个别图片人工修补。
- GitHub 仓库只包含源码和说明，不包含你的作业照片或处理结果。
