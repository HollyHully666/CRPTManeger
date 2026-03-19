from pathlib import Path
from PIL import Image
from pylibdmtx.pylibdmtx import decode as dmtx_decode
from multiprocessing import Pool, cpu_count
from typing import Dict, List, Tuple
import numpy as np

def process_chunk(chunk: List[Path]) -> List[Tuple[Path, List[str]]]:
    return [_decode_image(img) for img in chunk]

def _decode_image(image_path: Path) -> Tuple[Path, List[str]]:
    """Распознаёт DataMatrix с изображения. Несколько попыток с разными настройками для максимума распознаваний."""
    codes = []
    try:
        img = Image.open(image_path).convert('L')
        img_np = np.array(img)

        # Варианты препроцессинга для сложных изображений
        variants = [
            np.clip(img_np * 1.25, 0, 255).astype(np.uint8),  # усиление контраста
            img_np,  # без изменений
            (255 - img_np).astype(np.uint8),  # инверсия (светлый код на тёмном фоне)
            np.clip(img_np * 1.5, 0, 255).astype(np.uint8),  # сильнее контраст
        ]
        timeout_ms = 2000
        for arr in variants:
            for shrink in (1, 2, 3, 4, 5):
                decoded_objects = dmtx_decode(arr, timeout=timeout_ms, max_count=1, shrink=shrink)
                if decoded_objects:
                    codes = [obj.data.decode('utf-8', errors='replace') for obj in decoded_objects]
                    return image_path, codes
    except Exception:
        pass
    return image_path, []

def extract_datamatrix_from_image(
    data_matrix_dir: Path, reports_dir: Path
) -> Tuple[Dict[str, List[str]], Dict[str, object]]:
    """
    Распознаёт DataMatrix со всех PNG в подпапках data_matrix_dir.
    Возвращает (extracted_codes_by_pdf, stats):
    - В списке кодов по каждому PDF ровно один элемент на каждое изображение (пустая строка при неудаче).
    - stats: total_images, total_decoded, total_failed, failed_by_pdf.
    """
    extracted_codes_by_pdf = {}
    stats = {
        "total_images": 0,
        "total_decoded": 0,
        "total_failed": 0,
        "failed_by_pdf": {},
    }

    pdf_dirs = sorted(d for d in data_matrix_dir.iterdir() if d.is_dir())
    if not pdf_dirs:
        return extracted_codes_by_pdf, stats

    num_processes = max(1, cpu_count() - 1)

    for pdf_dir in pdf_dirs:
        pdf_name = pdf_dir.name
        image_files = sorted(pdf_dir.glob("*.png"))
        if not image_files:
            continue

        chunk_size = max(1, len(image_files) // num_processes + 1)
        image_chunks = [image_files[i : i + chunk_size] for i in range(0, len(image_files), chunk_size)]

        with Pool(processes=num_processes) as pool:
            results = pool.map(process_chunk, image_chunks)

        # Восстанавливаем порядок по имени файла (страницы по порядку)
        all_pairs: List[Tuple[Path, List[str]]] = []
        for chunk_result in results:
            all_pairs.extend(chunk_result)
        all_pairs.sort(key=lambda x: x[0].name)

        # Один код на изображение; при неудаче распознавания — пустая строка
        codes = []
        failed = 0
        for image_path, image_codes in all_pairs:
            if image_codes:
                codes.append(image_codes[0])
            else:
                codes.append("")
                failed += 1

        stats["total_images"] += len(codes)
        stats["total_decoded"] += (len(codes) - failed)
        stats["total_failed"] += failed
        if failed:
            stats["failed_by_pdf"][pdf_name] = failed

        extracted_codes_by_pdf[pdf_name] = codes

    return extracted_codes_by_pdf, stats