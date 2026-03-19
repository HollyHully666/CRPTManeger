"""
Объединяет XLSX-файлы из папки ИТОГ/Ввод в оборот в файлы по 30 000 кодов.
Результат: Ввод_в_оборот_все_part1.xlsx, part2.xlsx, ...
"""
from pathlib import Path
import pandas as pd

MAX_CODES_PER_TEMPLATE = 30000

def merge_input_xlsx():
    base = Path(__file__).resolve().parent
    input_dir = base / "ИТОГ" / "Ввод в оборот"
    if not input_dir.exists():
        print(f"Папка не найдена: {input_dir}")
        return

    xlsx_files = sorted(input_dir.glob("*.xlsx"))
    if not xlsx_files:
        print("В папке нет XLSX-файлов.")
        return

    dfs = []
    for f in xlsx_files:
        try:
            df = pd.read_excel(f, header=None)
            if not df.empty:
                dfs.append(df)
        except Exception as e:
            print(f"Ошибка при чтении {f.name}: {e}")

    if not dfs:
        print("Не удалось прочитать ни один файл.")
        return

    combined = pd.concat(dfs, ignore_index=True)
    for part_num, start in enumerate(range(0, len(combined), MAX_CODES_PER_TEMPLATE), start=1):
        chunk = combined.iloc[start : start + MAX_CODES_PER_TEMPLATE]
        out_path = input_dir / f"Ввод_в_оборот_все_part{part_num}.xlsx"
        chunk.to_excel(out_path, index=False, header=False)
        print(f"Файл: {out_path} (строк: {len(chunk)})")
    print(f"Объединено исходных файлов: {len(dfs)}, всего строк: {len(combined)}.")

if __name__ == "__main__":
    merge_input_xlsx()
