from pathlib import Path
import sys
import os

def create_output_structure() -> dict:
    # Путь к директории .exe
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent / "source"
    else:
        base_dir = Path("source")

    uploaded_pdf_dir = base_dir / "ЗагруженныеPDF"
    data_matrix_dir = base_dir / "DATA MATRIX"
    reports_dir = base_dir.parent / "ИТОГ" / "Отчеты о нанесении"
    input_dir = base_dir.parent / "ИТОГ" / "Ввод в оборот"
    upd_dir = base_dir.parent / "ИТОГ" / "Для УПД"

    for directory in [base_dir, uploaded_pdf_dir, data_matrix_dir, reports_dir, input_dir, upd_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    return {
        "uploaded_pdf": uploaded_pdf_dir,
        "data_matrix": data_matrix_dir,
        "reports": reports_dir,
        "input_folder": input_dir,
        "upd_folder": upd_dir
    }