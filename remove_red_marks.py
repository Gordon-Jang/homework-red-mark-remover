from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:
    print("缺少依赖: opencv-python")
    print("请先双击 install_dependencies.bat，或运行: python -m pip install opencv-python")
    sys.exit(1)


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def imread_unicode(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite_unicode(path: Path, image) -> bool:
    suffix = path.suffix.lower()
    ext = ".jpg" if suffix in {".jpeg", ".jpg"} else suffix
    ok, encoded = cv2.imencode(ext, image)
    if not ok:
        return False
    encoded.tofile(str(path))
    return True


def build_red_mask(
    image_bgr,
    saturation_min: int,
    value_min: int,
    red_strength: int,
    expand_px: int,
    min_area: int,
):
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

    # Red wraps around hue 0 in HSV, so use two ranges.
    lower_red_1 = np.array([0, saturation_min, value_min], dtype=np.uint8)
    upper_red_1 = np.array([12, 255, 255], dtype=np.uint8)
    lower_red_2 = np.array([165, saturation_min, value_min], dtype=np.uint8)
    upper_red_2 = np.array([179, 255, 255], dtype=np.uint8)

    mask_hsv = cv2.inRange(hsv, lower_red_1, upper_red_1)
    mask_hsv = cv2.bitwise_or(mask_hsv, cv2.inRange(hsv, lower_red_2, upper_red_2))

    b, g, r = cv2.split(image_bgr)
    red_dominant = (
        (r.astype(np.int16) - np.maximum(g, b).astype(np.int16)) >= red_strength
    ).astype(np.uint8) * 255

    mask = cv2.bitwise_and(mask_hsv, red_dominant)

    if min_area > 0:
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        filtered = np.zeros_like(mask)
        for label in range(1, num_labels):
            if stats[label, cv2.CC_STAT_AREA] >= min_area:
                filtered[labels == label] = 255
        mask = filtered

    if expand_px > 0:
        kernel_size = expand_px * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        mask = cv2.dilate(mask, kernel, iterations=1)

    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    _, mask = cv2.threshold(mask, 20, 255, cv2.THRESH_BINARY)
    return mask


def build_ghost_mask(
    image_bgr,
    red_strength: int,
    saturation_min: int,
    value_min: int,
    lab_a_min: int,
    expand_px: int,
    min_area: int,
):
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    h, s, v = cv2.split(hsv)
    _, a, _ = cv2.split(lab)
    b, g, r = cv2.split(image_bgr)

    red_delta = r.astype(np.int16) - np.maximum(g, b).astype(np.int16)
    red_hue = (h <= 18) | (h >= 155)
    bright_paper = v >= value_min

    hsv_faint_red = (
        bright_paper
        & red_hue
        & (s >= saturation_min)
        & (red_delta >= red_strength)
    )
    lab_faint_red = (
        bright_paper
        & (a.astype(np.int16) >= lab_a_min)
        & (red_delta >= max(4, red_strength - 3))
    )

    mask = np.where(hsv_faint_red | lab_faint_red, 255, 0).astype(np.uint8)

    if min_area > 0:
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        filtered = np.zeros_like(mask)
        for label in range(1, num_labels):
            if stats[label, cv2.CC_STAT_AREA] >= min_area:
                filtered[labels == label] = 255
        mask = filtered

    if expand_px > 0:
        kernel_size = expand_px * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        mask = cv2.dilate(mask, kernel, iterations=1)

    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    _, mask = cv2.threshold(mask, 20, 255, cv2.THRESH_BINARY)
    return mask


def dilate_mask(mask, radius_px: int):
    if radius_px <= 0:
        return mask
    kernel_size = radius_px * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    return cv2.dilate(mask, kernel, iterations=1)


def make_preview(original, cleaned, mask):
    mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    mask_overlay = original.copy()
    mask_overlay[mask > 0] = (0, 0, 255)
    mask_overlay = cv2.addWeighted(original, 0.65, mask_overlay, 0.35, 0)

    h = original.shape[0]
    separator = np.full((h, 8, 3), 220, dtype=np.uint8)
    return np.hstack([original, separator, mask_overlay, separator, cleaned])


def desaturate_red_ghosts(image_bgr, ghost_mask):
    if not np.any(ghost_mask):
        return image_bgr

    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    neutral_a = np.full_like(a, 128)
    neutral_b = cv2.GaussianBlur(b, (7, 7), 0)
    neutral_lab = cv2.merge([l, neutral_a, neutral_b])
    neutral_bgr = cv2.cvtColor(neutral_lab, cv2.COLOR_LAB2BGR)

    feather = cv2.GaussianBlur(ghost_mask, (0, 0), 1.2).astype(np.float32) / 255.0
    feather = feather[:, :, None]
    blended = image_bgr.astype(np.float32) * (1.0 - feather) + neutral_bgr.astype(np.float32) * feather
    return np.clip(blended, 0, 255).astype(np.uint8)


def process_image(src: Path, args) -> tuple[bool, str]:
    image = imread_unicode(src)
    if image is None:
        return False, "读取失败"

    mask = build_red_mask(
        image,
        saturation_min=args.saturation_min,
        value_min=args.value_min,
        red_strength=args.red_strength,
        expand_px=args.expand_px,
        min_area=args.min_area,
    )

    cleaned = cv2.inpaint(image, mask, args.radius, cv2.INPAINT_TELEA)
    combined_mask = mask.copy()
    ghost_pixels = 0

    if args.ghost_mode:
        for _ in range(args.ghost_passes):
            ghost_mask = build_ghost_mask(
                cleaned,
                red_strength=args.ghost_red_strength,
                saturation_min=args.ghost_saturation_min,
                value_min=args.ghost_value_min,
                lab_a_min=args.ghost_lab_a_min,
                expand_px=args.ghost_expand_px,
                min_area=args.ghost_min_area,
            )
            current_pixels = int(np.count_nonzero(ghost_mask))
            if current_pixels == 0:
                break
            if args.ghost_near_red_px > 0:
                near_red = dilate_mask(mask, args.ghost_near_red_px)
                ghost_mask = cv2.bitwise_and(ghost_mask, near_red)
                current_pixels = int(np.count_nonzero(ghost_mask))
                if current_pixels == 0:
                    break
            ghost_pixels += current_pixels
            combined_mask = cv2.bitwise_or(combined_mask, ghost_mask)
            if args.ghost_desaturate:
                cleaned = desaturate_red_ghosts(cleaned, ghost_mask)
            else:
                cleaned = cv2.inpaint(cleaned, ghost_mask, args.ghost_radius, cv2.INPAINT_TELEA)

    rel = src.relative_to(args.input_dir)
    output_path = (args.output_dir / rel).with_suffix(src.suffix)
    mask_path = (args.mask_dir / rel).with_suffix(".png")
    preview_path = (args.preview_dir / rel).with_suffix(".jpg")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)

    if not imwrite_unicode(output_path, cleaned):
        return False, "保存修复图失败"
    if not imwrite_unicode(mask_path, combined_mask):
        return False, "保存蒙版失败"
    if args.preview:
        if not imwrite_unicode(preview_path, make_preview(image, cleaned, combined_mask)):
            return False, "保存预览图失败"

    red_pixels = int(np.count_nonzero(mask))
    combined_pixels = int(np.count_nonzero(combined_mask))
    return True, f"OK red_pixels={red_pixels} ghost_pixels={ghost_pixels} combined_pixels={combined_pixels}"


def parse_args():
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="批量检测红色批改痕迹并用 OpenCV inpaint 修复。"
    )
    parser.add_argument("--input-dir", type=Path, default=base / "input_images")
    parser.add_argument("--output-dir", type=Path, default=base / "output_clean")
    parser.add_argument("--mask-dir", type=Path, default=base / "masks")
    parser.add_argument("--preview-dir", type=Path, default=base / "previews")
    parser.add_argument("--only", default="", help="只处理文件名包含该文本的图片")
    parser.add_argument("--saturation-min", type=int, default=70)
    parser.add_argument("--value-min", type=int, default=50)
    parser.add_argument("--red-strength", type=int, default=35)
    parser.add_argument("--expand-px", type=int, default=2)
    parser.add_argument("--radius", type=float, default=3.0)
    parser.add_argument("--min-area", type=int, default=4)
    parser.add_argument("--ghost-mode", action="store_true")
    parser.add_argument("--ghost-passes", type=int, default=2)
    parser.add_argument("--ghost-saturation-min", type=int, default=18)
    parser.add_argument("--ghost-value-min", type=int, default=95)
    parser.add_argument("--ghost-red-strength", type=int, default=7)
    parser.add_argument("--ghost-lab-a-min", type=int, default=132)
    parser.add_argument("--ghost-expand-px", type=int, default=2)
    parser.add_argument("--ghost-radius", type=float, default=4.0)
    parser.add_argument("--ghost-min-area", type=int, default=10)
    parser.add_argument("--ghost-desaturate", action="store_true")
    parser.add_argument("--ghost-near-red-px", type=int, default=0)
    parser.add_argument("--no-preview", dest="preview", action="store_false")
    parser.set_defaults(preview=True)
    args = parser.parse_args()

    args.input_dir = args.input_dir.resolve()
    args.output_dir = args.output_dir.resolve()
    args.mask_dir = args.mask_dir.resolve()
    args.preview_dir = args.preview_dir.resolve()
    return args


def main() -> int:
    args = parse_args()
    if not args.input_dir.exists():
        print(f"输入文件夹不存在: {args.input_dir}")
        return 2

    images = [
        p
        for p in args.input_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if args.only:
        images = [p for p in images if args.only.lower() in p.name.lower()]
    if not images:
        print(f"没有找到图片。请把图片放入: {args.input_dir}")
        if args.only:
            print(f"当前 --only 过滤条件: {args.only}")
        return 1

    print(f"输入: {args.input_dir}")
    print(f"输出: {args.output_dir}")
    print(f"蒙版: {args.mask_dir}")
    print(f"预览: {args.preview_dir}")
    print(f"共 {len(images)} 张图片")

    ok_count = 0
    for index, src in enumerate(images, start=1):
        ok, message = process_image(src, args)
        status = "OK" if ok else "FAIL"
        print(f"[{index}/{len(images)}] {status} {src.name} - {message}")
        ok_count += 1 if ok else 0

    print(f"完成: {ok_count}/{len(images)}")
    return 0 if ok_count == len(images) else 3


if __name__ == "__main__":
    raise SystemExit(main())
