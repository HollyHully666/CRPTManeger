from pathlib import Path
import logging
from pdf2image import convert_from_path
from multiprocessing import Pool, cpu_count
from typing import Dict, List, Tuple
import shutil

if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _convert_single_pdf(args: Tuple[Path, Path, str | None]) -> Tuple[str, List[Path]]:
    pdf_path, data_matrix_dir, poppler_path = args
    pdf_name = pdf_path.stem
    image_dir = data_matrix_dir / pdf_name
    image_paths = []
    try:
        #logging.info(f"Начинаю обработку файла: {pdf_path.name}")
        # Очищаем или создаём подпапку для PNG
        if image_dir.exists():
            shutil.rmtree(image_dir)
        image_dir.mkdir(parents=True, exist_ok=True)
        
        images = convert_from_path(
            pdf_path=pdf_path,
            dpi=150,
            poppler_path=poppler_path,
            thread_count=4
        )
        for i, image in enumerate(images, start=1):
            image_path = image_dir / f"{pdf_name}_{i}.png"
            image.save(image_path, "PNG", optimize=True)
            image_paths.append(image_path)
            #logging.info(f"Сохранена страница {i} как: {image_path}")
        #logging.info(f"Успешно обработан файл: {pdf_path.name}. Сгенерировано {len(images)} изображений")
        return pdf_name, image_paths
    except Exception as e:
        #logging.error(f"Ошибка при обработке {pdf_path.name}: {e}")
        return pdf_name, []

def convert_pdf_to_images(uploaded_pdf_dir: Path, data_matrix_dir: Path, poppler_path: str | None = None) -> Dict[str, List[Path]]:
    """
    Конвертирует PDF-файлы из uploaded_pdf_dir в PNG и сохраняет их в data_matrix_dir/<pdf_name>.
    Args:
        uploaded_pdf_dir (Path): Путь к папке с PDF-файлами (source/ЗагруженныеPDF).
        data_matrix_dir (Path): Путь к папке для PNG (source/DATA MATRIX).
        poppler_path (str, optional): Путь к Poppler.
    Returns:
        Dict[str, List[Path]]: Словарь с именами PDF и списками путей к PNG.
    """
    processed_pdfs_info = {}
    pdf_files = list(uploaded_pdf_dir.glob("*.pdf"))
    if not pdf_files:
        #logging.warning(f"Не найдено PDF-файлов в {uploaded_pdf_dir}")
        return processed_pdfs_info

    # Очищаем старые подпапки в data_matrix_dir, оставляя саму папку
    for item in data_matrix_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
    
    num_processes = max(1, cpu_count() - 1)
    args = [(pdf_file, data_matrix_dir, poppler_path) for pdf_file in pdf_files]

    with Pool(processes=num_processes) as pool:
        results = pool.map(_convert_single_pdf, args)

    for pdf_name, image_paths in results:
        if image_paths:
            processed_pdfs_info[pdf_name] = image_paths

    return processed_pdfs_info