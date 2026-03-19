from pathlib import Path  # Импорт Path для работы с путями файловой системы
import logging  # Модуль для логирования
import logging.handlers  # Дополнительные обработчики логов (например, ротация файлов)
from datetime import datetime  # Дата и время для меток и имён файлов
import shutil  # Операции с файлами и папками (копирование, удаление)
import zipfile  # Работа с ZIP-архивами
import tkinter as tk  # Библиотека Tkinter для GUI
from tkinter import filedialog  # Диалог выбора файлов
from typing import List  # Аннотация типа: список

try:
    import rarfile  # type: ignore[import]  # Работа с RAR-архивами (необязательный модуль)
except ImportError:  # Если модуль не установлен, просто отключаем поддержку RAR с сообщением в логах
    rarfile = None  # type: ignore[assignment]

from Modules.createOutputStructure import create_output_structure  # Создание структуры выходных папок
from Modules.pdf_to_png import convert_pdf_to_images  # Конвертация PDF в изображения PNG
from Modules.decode_datamatrix import extract_datamatrix_from_image  # Извлечение DataMatrix-кодов с изображений
from Modules.format_kiz_code import format_kiz_code  # Форматирование КИЗ-кодов
from Modules.get_product_data import get_product_data  # Получение данных о товарах
from Modules.generate_final_csv import generate_final_csv  # Генерация итогового CSV для УПД
import pandas as pd  # Работа с табличными данными

# Максимальное количество кодов в одном шаблоне (ограничение Честного знака)
MAX_CODES_PER_TEMPLATE = 30000

def setup_logging(log_dir: Path) -> None:  # Настройка логирования (консоль + файл с ротацией)
    log_dir.mkdir(parents=True, exist_ok=True)  # Создаём директорию для логов, если её нет
    log_file = log_dir / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"  # Имя файла лога с меткой времени
    logger = logging.getLogger()  # Получаем корневой логгер
    if not logger.handlers:  # Добавляем обработчики только один раз
        logger.setLevel(logging.INFO)  # Устанавливаем уровень логирования INFO
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  # Формат сообщения лога
        console_handler = logging.StreamHandler()  # Обработчик вывода в консоль
        console_handler.setFormatter(log_format)  # Применяем формат для консоли
        logger.addHandler(console_handler)  # Регистрируем обработчик консоли
        file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)  # Файловый обработчик с ротацией
        file_handler.setFormatter(log_format)  # Применяем формат для файла
        logger.addHandler(file_handler)  # Регистрируем файловый обработчик

def _prepare_file_dialog_root():
    """Создаёт окно Tk для диалога и поднимает его поверх остальных (чтобы не терялось за консолью)."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update_idletasks()
    root.lift()
    root.focus_force()
    root.update()
    return root


def select_pdf_files() -> List[Path]:
    root = _prepare_file_dialog_root()
    try:
        file_paths = filedialog.askopenfilenames(
            title="Выберите PDF или архивы (PDF, ZIP, RAR)",
            filetypes=[
                ("Все файлы", "*.*"),
                ("PDF файлы", "*.pdf"),
                ("Архивы ZIP", "*.zip"),
                ("Архивы RAR", "*.rar"),
                ("Все поддерживаемые", "*.pdf *.zip *.rar"),
            ],
            parent=root,
        )
        return [Path(p) for p in file_paths] if file_paths else []
    finally:
        root.destroy()


def select_pdf_folders() -> List[Path]:
    root = _prepare_file_dialog_root()
    folders: List[Path] = []
    try:
        while True:
            folder = filedialog.askdirectory(
                title="Выберите папку с PDF (Отмена — закончить выбор папок)",
                parent=root,
            )
            if not folder:
                break
            p = Path(folder)
            if p not in folders:
                folders.append(p)
    finally:
        root.destroy()
    if not folders:
        return []
    seen: set[Path] = set()
    result: List[Path] = []
    for folder in folders:
        for p in sorted(folder.rglob("*")):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".pdf", ".zip", ".rar"}:
                continue
            if p not in seen:
                seen.add(p)
                result.append(p)
    return result


def copy_pdf_to_uploaded_dir(pdf_files: List[Path], uploaded_pdf_dir: Path) -> None:
    """Копирует PDF в служебную папку, переименовывая по порядку (1.pdf, 2.pdf, ...).
    Так одноимённые файлы из разных папок не перезаписывают друг друга.
    Пример: папка «Январь» содержит отчёт.pdf (100 кодов), папка «Февраль» — тоже отчёт.pdf (200 кодов).
    Без переименования второй файл затёр бы первый; с переименованием получаем 1.pdf и 2.pdf — оба обрабатываются."""
    uploaded_pdf_dir.mkdir(parents=True, exist_ok=True)
    for item in uploaded_pdf_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    for i, pdf_file in enumerate(pdf_files, start=1):
        try:
            dest_path = uploaded_pdf_dir / f"{i}.pdf"
            shutil.copy(pdf_file, dest_path)
            logging.info(f"  [{i}] {pdf_file.name} -> {dest_path.name}")
        except Exception as e:
            logging.error(f"Ошибка при копировании {pdf_file}: {e}")


def _collect_pdfs_under(root: Path) -> list[Path]:
    """Рекурсивно находит все PDF под указанной директорией."""
    return sorted(p for p in root.rglob("*.pdf") if p.is_file())


def _expand_archives(paths: List[Path], source_dir: Path) -> List[Path]:
    """Обрабатывает ZIP/RAR среди выбранных путей: распаковывает и возвращает список всех PDF.

    - Обычные PDF возвращаются как есть.
    - ZIP/RAR распаковываются во временную папку внутри source_dir.
    - Если внутри архива есть одна папка с именем, совпадающим с именем архива — проваливаемся в неё.
    - Далее рекурсивно собираем все PDF.
    """
    pdf_files: list[Path] = []
    archives: list[Path] = []

    for p in paths:
        suffix = p.suffix.lower()
        if suffix == ".pdf":
            pdf_files.append(p)
        elif suffix in {".zip", ".rar"}:
            archives.append(p)
        else:
            logging.warning(f"Игнорирую неподдерживаемый файл: {p}")

    if not archives:
        return pdf_files

    archives_root = source_dir / "_РАСПАКОВАННЫЕ_АРХИВЫ"
    if archives_root.exists():
        try:
            shutil.rmtree(archives_root)
        except Exception as e:
            logging.warning(f"Не удалось очистить временную папку архивов {archives_root}: {e}")
    archives_root.mkdir(parents=True, exist_ok=True)

    for arch in archives:
        arch_dir = archives_root / arch.stem
        arch_dir.mkdir(parents=True, exist_ok=True)
        suffix = arch.suffix.lower()
        try:
            if suffix == ".zip":
                with zipfile.ZipFile(arch, "r") as zf:
                    zf.extractall(arch_dir)
            elif suffix == ".rar":
                if rarfile is None:
                    logging.error(
                        f"RAR-архив {arch} пропущен: модуль 'rarfile' не установлен. "
                        f"Установите его командой 'pip install rarfile' и убедитесь, что в системе есть unrar."
                    )
                    continue
                with rarfile.RarFile(arch) as rf:  # type: ignore[operator]
                    rf.extractall(arch_dir)
            else:
                logging.warning(f"Архив с неподдерживаемым расширением пропущен: {arch}")
                continue
        except Exception as e:
            logging.error(f"Ошибка при распаковке архива {arch}: {e}")
            continue

        root = arch_dir
        subdirs = [d for d in root.iterdir() if d.is_dir()]
        if len(subdirs) == 1 and subdirs[0].name == arch.stem:
            root = subdirs[0]

        archive_pdfs = _collect_pdfs_under(root)
        if not archive_pdfs:
            logging.warning(f"В архиве {arch} не найдено ни одного PDF-файла.")
        else:
            logging.info(f"Из архива {arch} найдено PDF: {len(archive_pdfs)}")
            pdf_files.extend(archive_pdfs)

    return pdf_files

def clear_source_dir(source_dir: Path) -> None:  # Полная очистка и пересоздание служебной директории
    try:
        if source_dir.exists():  # Если директория существует
            shutil.rmtree(source_dir)  # Удаляем её рекурсивно
            logging.info(f"Папка {source_dir} очищена")  # Сообщаем об очистке
        create_output_structure()  # Пересоздаём стандартную структуру папок
        logging.info(f"Папка {source_dir} пересоздана")  # Сообщаем о пересоздании
    except Exception as e:
        logging.error(f"Ошибка при очистке {source_dir}: {e}")  # Логируем ошибку

def clear_itog_subdirs(full_codes_dir: Path, input_dir: Path, reports_dir: Path, upd_dir: Path) -> None:
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    for dir_path in [full_codes_dir, input_dir, reports_dir, upd_dir]:
        try:
            if dir_path.exists():  # Если папка существует
                for item in dir_path.iterdir():  # Перебираем содержимое
                    if item.is_file():  # Это файл
                        item.unlink()  # Удаляем файл
                    elif item.is_dir():  # Это папка
                        shutil.rmtree(item)  # Удаляем папку рекурсивно
                logging.info(f"Содержимое папки {dir_path} очищено")  # Сообщаем об очистке
        except Exception as e:
            logging.error(f"Ошибка при очистке {dir_path}: {e}")  # Логируем ошибку

def _chunk_list(lst: list, chunk_size: int):
    """Разбивает список на части не больше chunk_size элементов."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


def _normalize_code_for_duplicate(raw_code: str) -> str | None:
    """Приводит сырой код к короткой форме (как в format_kiz_code) для сравнения дубликатов."""
    code = raw_code.strip()
    if not code:
        return None
    gs_index = code.find("\x1D")
    if gs_index == 24:
        return code[:24]
    if gs_index == 31:
        return code[:31]
    if len(code) < 24:
        return code
    return code[:31] if len(code) >= 31 else code


def collect_duplicate_report(extracted_codes_by_pdf: dict[str, list]) -> dict:
    """
    Анализирует коды по PDF и находит дубликаты.
    Возвращает словарь: {
        "by_code": { normalized_code: { "pdf_name": count, ... }, ... },  # только коды с повторами
        "unique_duplicated_count": int,   # сколько уникальных кодов встречались > 1 раза
        "total_duplicate_occurrences": int,  # сколько лишних вхождений (сумма (n-1) по каждому коду)
        "pdfs_with_duplicates": set,     # в каких PDF есть хотя бы один дубликат
    }
    """
    code_occurrences: dict[str, dict[str, int]] = {}
    for pdf_name, codes in extracted_codes_by_pdf.items():
        for code in codes:
            short = _normalize_code_for_duplicate(code)
            if not short:
                continue
            code_occurrences.setdefault(short, {})
            code_occurrences[short][pdf_name] = code_occurrences[short].get(pdf_name, 0) + 1

    duplicated = {
        code: pdf_counts
        for code, pdf_counts in code_occurrences.items()
        if sum(pdf_counts.values()) > 1
    }

    total_duplicate_occurrences = sum(
        sum(pdf_counts.values()) - 1 for pdf_counts in duplicated.values()
    )
    pdfs_with_duplicates = set()
    for pdf_counts in duplicated.values():
        pdfs_with_duplicates.update(pdf_counts.keys())

    return {
        "by_code": duplicated,
        "unique_duplicated_count": len(duplicated),
        "total_duplicate_occurrences": total_duplicate_occurrences,
        "pdfs_with_duplicates": sorted(pdfs_with_duplicates),
    }


def log_duplicate_report(duplicate_report: dict) -> None:
    """Пишет в лог сводку по дубликатам кодов."""
    if not duplicate_report["by_code"]:
        logging.info("Дубликатов кодов не обнаружено.")
        return
    dup = duplicate_report
    logging.info("--- Отчёт о дубликатах кодов ---")
    logging.info(f"Уникальных кодов с повторениями: {dup['unique_duplicated_count']}")
    logging.info(f"Всего лишних вхождений (дубликатов): {dup['total_duplicate_occurrences']}")
    logging.info(f"Дубликаты найдены в PDF-файлах: {', '.join(dup['pdfs_with_duplicates'])}")
    for code, pdf_counts in list(dup["by_code"].items())[:20]:  # первые 20 кодов детально
        parts = [f"{name}: {cnt}" for name, cnt in sorted(pdf_counts.items())]
        logging.info(f"  Код …{code[-8:]}: {', '.join(parts)}")
    if len(dup["by_code"]) > 20:
        logging.info(f"  ... и ещё {len(dup['by_code']) - 20} кодов с дубликатами.")
    logging.info("--------------------------------")


def save_to_xlsx(codes_dict: dict, input_dir: Path):  # Сохранение коротких кодов в XLSX (для ввода в оборот)
    for pdf_name, codes in codes_dict.items():  # Перебор PDF и их списков кодов
        for part_num, chunk in enumerate(_chunk_list(codes, MAX_CODES_PER_TEMPLATE), start=1):
            df = pd.DataFrame(chunk)
            base_name = pdf_name if part_num == 1 else f"{pdf_name}_part{part_num}"
            xlsx_path = input_dir / f"{base_name}.xlsx"
            df.to_excel(xlsx_path, index=False, header=False)

def merge_input_xlsx_files(input_dir: Path) -> None:  # Объединение XLSX из папки «Ввод в оборот» в файлы по 30k кодов
    xlsx_files = sorted(input_dir.glob("*.xlsx"))
    if not xlsx_files:
        return
    dfs = []
    for f in xlsx_files:
        try:
            df = pd.read_excel(f, header=None)
            if not df.empty:
                dfs.append(df)
        except Exception as e:
            logging.warning(f"Не удалось прочитать {f.name}: {e}")
    if not dfs:
        return
    combined = pd.concat(dfs, ignore_index=True)
    for part_num, start in enumerate(range(0, len(combined), MAX_CODES_PER_TEMPLATE), start=1):
        chunk = combined.iloc[start : start + MAX_CODES_PER_TEMPLATE]
        out_path = input_dir / f"Ввод_в_оборот_все_part{part_num}.xlsx"
        chunk.to_excel(out_path, index=False, header=False)
        logging.info(f"Файл: {out_path} (строк: {len(chunk)})")


def save_full_codes(extracted_codes_by_pdf: dict, full_codes_dir: Path) -> None:
    """Сохраняет полные (сырые) коды сразу после сканирования в папку «Полные коды».

    - По одному файлу на PDF
    - И один общий файл со всеми кодами
    """
    full_codes_dir.mkdir(parents=True, exist_ok=True)
    all_codes_path = full_codes_dir / "_all_full_codes.txt"
    all_codes: list[str] = []
    for pdf_name, codes in extracted_codes_by_pdf.items():
        path = full_codes_dir / f"{pdf_name}.txt"
        with open(path, "w", encoding="utf-8") as f:
            for code in codes:
                line = (code.strip() if code else "") + "\n"
                f.write(line)
                all_codes.append(line)

    with open(all_codes_path, "w", encoding="utf-8") as f:
        f.writelines(all_codes)
    logging.info(f"Полные коды сохранены в {full_codes_dir}")


def archive_itog_folder(itog_dir: Path) -> None:
    """Упаковывает содержимое папки «ИТОГ» в ZIP-архив внутри этой же папки."""
    if not itog_dir.exists():
        logging.warning(f"Папка ИТОГ не найдена: {itog_dir}")
        return

    archive_path = itog_dir / "ИТОГ_результаты.zip"
    try:
        if archive_path.exists():
            archive_path.unlink()
    except Exception as e:
        logging.warning(f"Не удалось удалить старый архив {archive_path}: {e}")

    try:
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in itog_dir.rglob("*"):
                if not path.is_file():
                    continue
                rel_path = path.relative_to(itog_dir)
                # Не добавляем сам архив внутрь него же
                if path.resolve() == archive_path.resolve() or rel_path == Path(archive_path.name):
                    continue
                zf.write(path, rel_path)
        logging.info(f"Итоговые файлы упакованы в архив: {archive_path}")
    except Exception as e:
        logging.error(f"Ошибка при упаковке папки ИТОГ в архив: {e}")


def save_to_csv(extracted_codes: dict, reports_dir: Path):  # Сохранение распознанных кодов в CSV (отчёт о нанесении)
    for pdf_name, codes in extracted_codes.items():
        codes = [c for c in codes if (c or "").strip()]  # только распознанные, без пустых
        for part_num, chunk in enumerate(_chunk_list(codes, MAX_CODES_PER_TEMPLATE), start=1):
            df = pd.DataFrame(chunk)
            base_name = pdf_name if part_num == 1 else f"{pdf_name}_part{part_num}"
            csv_path = reports_dir / f"{base_name}.csv"
            df.to_csv(csv_path, index=False, header=False, encoding="utf-8")

def merge_reports_csv_files(reports_dir: Path) -> None:  # Объединение CSV из папки «Отчеты о нанесении» в файлы по 30k кодов
    csv_files = sorted(reports_dir.glob("*.csv"))
    if not csv_files:
        return
    dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, header=None, encoding="utf-8")
            if not df.empty:
                dfs.append(df)
        except Exception as e:
            logging.warning(f"Не удалось прочитать {f.name}: {e}")
    if not dfs:
        return
    combined = pd.concat(dfs, ignore_index=True)
    for part_num, start in enumerate(range(0, len(combined), MAX_CODES_PER_TEMPLATE), start=1):
        chunk = combined.iloc[start : start + MAX_CODES_PER_TEMPLATE]
        out_path = reports_dir / f"Отчеты_о_нанесении_все_part{part_num}.csv"
        chunk.to_csv(out_path, index=False, header=False, encoding="utf-8")
        logging.info(f"Файл: {out_path} (строк: {len(chunk)})")

def main():
    try:
        paths = create_output_structure()
        uploaded_pdf_dir = paths["uploaded_pdf"]
        data_matrix_dir = paths["data_matrix"]
        full_codes_dir = paths["full_codes"]
        reports_dir = paths["reports"]
        input_dir = paths["input_folder"]
        upd_dir = paths["upd_folder"]
        source_dir = uploaded_pdf_dir.parent
        setup_logging(source_dir)
        clear_itog_subdirs(full_codes_dir, input_dir, reports_dir, upd_dir)
    except Exception as e:
        logging.error(f"Не удалось создать структуру папок: {e}. Выход из программы")
        return

    logging.info("Откроется окно выбора файлов (если не видно — проверьте панель задач).")
    selected_paths = select_pdf_files()
    if selected_paths:
        pdf_files = _expand_archives(selected_paths, source_dir)
        if not pdf_files:
            logging.error("Не найдено ни одного PDF-файла среди выбранных файлов/архивов. Завершение работы")
            return
    else:
        logging.info("Файлы не выбраны. Откроется окно выбора папки (если не видно — проверьте панель задач).")
        folder_items = select_pdf_folders()
        if not folder_items:
            logging.error("Не выбрано ни одного файла или папки. Завершение работы")
            return
        pdf_files = _expand_archives(folder_items, source_dir)
        if not pdf_files:
            logging.error("В выбранных папках/архивах не найдено ни одного PDF-файла. Завершение работы")
            return

    logging.info(f"Найдено PDF к обработке: {len(pdf_files)} файлов")

    logging.info("Копирование и переименование PDF по порядковому номеру (1.pdf, 2.pdf, ...)...")
    copy_pdf_to_uploaded_dir(pdf_files, uploaded_pdf_dir)

    POPPLER_BIN_PATH = r"C:\Tools\poppler\Library\bin"

    logging.info("Конвертация PDF в PNG...")
    try:
        processed_pdfs_info = convert_pdf_to_images(uploaded_pdf_dir=uploaded_pdf_dir, data_matrix_dir=data_matrix_dir, poppler_path=POPPLER_BIN_PATH)
        if not processed_pdfs_info:
            logging.error("Не удалось конвертировать PDF-файлы. Завершение работы")
            return
        logging.info(f"Конвертировано PDF: {len(processed_pdfs_info)} файлов")
    except Exception as e:
        logging.error(f"Ошибка при конвертации PDF: {e}. Завершение работы")
        return

    choice = input("Что хотите получить на выходе? (1) Файлы для Ввода в оборот, (2) Файлы для отчета о нанесении, (3) Шаблон для загрузки УПД, (4) Все сразу (через пробел, например: 1 3): ")
    choices = [int(x) for x in choice.split() if x.isdigit()]
    if not choices:
        logging.error("Неверный ввод. Завершение работы")
        return

    if 4 in choices:
        choices = [1, 2, 3]
        logging.info("Выбран вариант 4: выполнение всех действий")

    logging.info("Распознавание DataMatrix-кодов...")
    try:
        extracted_codes_by_pdf, decode_stats = extract_datamatrix_from_image(
            data_matrix_dir=data_matrix_dir, reports_dir=reports_dir
        )
        if not extracted_codes_by_pdf:
            logging.error("Не удалось извлечь DataMatrix-коды. Завершение работы")
            return
    except Exception as e:
        logging.error(f"Ошибка при извлечении кодов: {e}. Завершение работы")
        return

    # Диагностика: где теряются коды (страницы vs распознавание)
    total_img = decode_stats.get("total_images", 0)
    total_dec = decode_stats.get("total_decoded", 0)
    total_fail = decode_stats.get("total_failed", 0)
    logging.info(f"Страниц (изображений): {total_img}, распознано кодов: {total_dec}, не распознано: {total_fail}")
    if total_fail and decode_stats.get("failed_by_pdf"):
        by_pdf = decode_stats["failed_by_pdf"]
        top_failed = sorted(by_pdf.items(), key=lambda x: -x[1])[:10]
        logging.info(f"Больше всего неудач по файлам: {', '.join(f'{k}({v})' for k, v in top_failed)}")

    save_full_codes(extracted_codes_by_pdf, full_codes_dir)

    logging.info("Обработка кодов для шаблонов...")
    duplicate_report = collect_duplicate_report(extracted_codes_by_pdf)

    short_codes_dict = {}
    formatted_codes_dict = {}
    code_types = {}
    format_stats = {}
    if 1 in choices or 3 in choices:
        logging.info("Форматирование КИЗ-кодов...")
        try:
            short_codes_dict, formatted_codes_dict, code_types, format_stats = format_kiz_code(
                extracted_codes_by_pdf=extracted_codes_by_pdf, include_short_codes=True, verbose=False
            )
            if not short_codes_dict:
                logging.error("Форматирование не вернуло данных. Завершение работы")
                return
            acc = format_stats.get("accepted", 0)
            se = format_stats.get("skipped_empty", 0)
            sf = format_stats.get("skipped_format", 0)
            st = format_stats.get("skipped_type_mismatch", 0)
            logging.info(
                f"После форматирования: принято {acc}, отброшено: пустые {se}, формат {sf}, другой тип в файле {st}"
            )
        except Exception as e:
            logging.error(f"Ошибка при форматировании кодов: {e}. Завершение работы")
            return

    if 1 in choices:
        save_to_xlsx(short_codes_dict, input_dir)
        merge_input_xlsx_files(input_dir)
        logging.info(f"Сохранено в XLSX в {input_dir}")

    if 2 in choices:
        save_to_csv(extracted_codes_by_pdf, reports_dir)
        merge_reports_csv_files(reports_dir)
        logging.info(f"Сохранено в CSV в {reports_dir}")

    if 3 in choices:
        logging.info("Запрос данных о товарах...")
        try:
            product_data = get_product_data(uploaded_pdf_dir=uploaded_pdf_dir, reports_dir=reports_dir, extracted_codes_by_pdf=extracted_codes_by_pdf, code_types=code_types)
            if not product_data:
                logging.error("Не получены данные о товарах. Завершение работы")
                return
        except Exception as e:
            logging.error(f"Ошибка при запросе данных о товарах: {e}. Завершение работы")
            return

        logging.info("Генерация итогового CSV...")
        try:
            output_csv_path = upd_dir / "final_upd.csv"
            written_csv_paths = generate_final_csv(
                formatted_codes=formatted_codes_dict,
                product_data=product_data,
                upd_dir=upd_dir,
                output_path=output_csv_path,
                max_codes_per_file=MAX_CODES_PER_TEMPLATE,
            )
            if written_csv_paths:
                for p in written_csv_paths:
                    logging.info(f"УПД: {p}")
        except Exception as e:
            logging.error(f"Ошибка при создании CSV: {e}. Завершение работы")
            return

    log_duplicate_report(duplicate_report)

    # Архивируем все результаты в папке «ИТОГ»
    itog_dir = full_codes_dir.parent
    archive_itog_folder(itog_dir)

    logging.info("Программа успешно завершена")

    clear_source_dir(source_dir)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Программа прервана пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
    finally:
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        paths = create_output_structure()
        source_dir = paths["uploaded_pdf"].parent
        clear_source_dir(source_dir)