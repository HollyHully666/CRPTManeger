from pathlib import Path
from PIL import Image
from pylibdmtx.pylibdmtx import decode as dmtx_decode
from multiprocessing import Pool, cpu_count
from typing import Dict, List, Tuple
import numpy as np

def process_chunk(chunk: List[Path]) -> List[Tuple[str, List[str]]]:
    return [_decode_image(img) for img in chunk]

def _decode_image(image_path: Path) -> Tuple[str, List[str]]:
    codes = []
    try:
        img = Image.open(image_path).convert('L')
        img_np = np.array(img)
        img_np = np.clip(img_np * 1.2, 0, 255).astype(np.uint8)
        decoded_objects = dmtx_decode(img_np, timeout=300, max_count=1, shrink=2)
        codes = [obj.data.decode('utf-8') for obj in decoded_objects]
        return image_path.name, codes
    except Exception as e:
        return image_path.name, []

def extract_datamatrix_from_image(data_matrix_dir: Path, reports_dir: Path, write_reports: bool = True) -> Dict[str, List[str]]:
    extracted_codes_by_pdf = {}

    pdf_dirs = [d for d in data_matrix_dir.iterdir() if d.is_dir()]
    if not pdf_dirs:
        return extracted_codes_by_pdf

    num_processes = max(1, cpu_count() - 1)

    for pdf_dir in pdf_dirs:
        pdf_name = pdf_dir.name
        image_files = list(pdf_dir.glob("*.png"))
        if not image_files:
            continue

        chunk_size = max(1, len(image_files) // num_processes + 1)
        image_chunks = [image_files[i:i + chunk_size] for i in range(0, len(image_files), chunk_size)]

        with Pool(processes=num_processes) as pool:
            results = pool.map(process_chunk, image_chunks)

        codes = []
        for chunk_result in results:
            for image_name, image_codes in chunk_result:
                if image_codes:
                    codes.extend(image_codes)

        if codes and write_reports:
            extracted_codes_by_pdf[pdf_name] = codes
            output_file = reports_dir / f"{pdf_name}.txt"
            try:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(codes))
            except OSError as e:
                pass
        elif codes:
            extracted_codes_by_pdf[pdf_name] = codes

    return extracted_codes_by_pdf