"""
Объединяет CSV-файлы из папки ИТОГ/Отчеты о нанесении в файлы по 30 000 кодов.
Результат: Отчеты_о_нанесении_все_part1.csv, part2.csv, ...
"""
from pathlib import Path
import pandas as pd

MAX_CODES_PER_TEMPLATE = 30000

def merge_reports_csv():
    base = Path(__file__).resolve().parent
    reports_dir = base / "ИТОГ" / "Отчеты о нанесении"
    if not reports_dir.exists():
        print(f"Папка не найдена: {reports_dir}")
        return

    csv_files = sorted(reports_dir.glob("*.csv"))
    if not csv_files:
        print("В папке нет CSV-файлов.")
        return

    dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, header=None, encoding="utf-8")
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
        out_path = reports_dir / f"Отчеты_о_нанесении_все_part{part_num}.csv"
        chunk.to_csv(out_path, index=False, header=False, encoding="utf-8")
        print(f"Файл: {out_path} (строк: {len(chunk)})")
    print(f"Объединено исходных файлов: {len(dfs)}, всего строк: {len(combined)}.")

if __name__ == "__main__":
    merge_reports_csv()
