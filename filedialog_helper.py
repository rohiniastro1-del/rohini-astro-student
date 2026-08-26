"""Показва нативен Windows диалог за запис/отваряне на .jhd файл.

Използва се от локалния сървър като отделен процес, защото Tk интерфейсът
трябва да работи върху главната нишка на собствения си процес.

Аргументи:
    save|open  - вид на диалога
    <начална папка>  - папка, в която да се отвори диалогът
    <име на файл>  - само за save: предложено име на файла

Изход: избраният път (или празен ред при отказ).
"""
import sys
import tkinter as tk
from tkinter import filedialog

FILE_TYPES = [("JHora файлове", "*.jhd"), ("Всички файлове", "*.*")]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("")
        return
    mode = sys.argv[1]
    initial_dir = sys.argv[2] if len(sys.argv) > 2 else ""
    initial_file = sys.argv[3] if len(sys.argv) > 3 else ""

    root = tk.Tk()
    try:
        # Диалогът трябва да има собственик. Без parent Windows понякога го
        # отваря зад основния прозорец и програмата изглежда блокирала.
        root.withdraw()
        root.attributes("-topmost", True)
        root.update_idletasks()
        root.lift()
        root.focus_force()

        if mode == "save":
            path = filedialog.asksaveasfilename(
                parent=root,
                initialdir=initial_dir or None,
                initialfile=initial_file,
                defaultextension=".jhd",
                filetypes=FILE_TYPES,
                title="Запази хороскоп",
            )
        else:
            path = filedialog.askopenfilename(
                parent=root,
                initialdir=initial_dir or None,
                filetypes=FILE_TYPES,
                title="Отвори хороскоп",
            )
    finally:
        root.destroy()
    print(path or "")


if __name__ == "__main__":
    main()
