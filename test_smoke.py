import os, tempfile, csv
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from haituo_qt import MainWindow, Sheet
from openpyxl import load_workbook
app = QApplication([])
w = MainWindow()
s = w.sheet()
s.setRowCount(4)
s.setColumnCount(3)
s.write_cell(0, 0, "Name")
s.write_cell(1, 0, "Alice")
s.write_cell(1, 1, "1234567890123456")
s.write_cell(2, 0, "Bob")
assert s.used_size() == (3, 2), s.used_size()
with tempfile.TemporaryDirectory() as d:
    csv_path = os.path.join(d, "sample.csv")
    assert w.write_file(csv_path)
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3, rows
    assert len(rows[0]) == 2, rows
    assert rows[1][1] == "1234567890123456"
    xlsx_path = os.path.join(d, "sample.xlsx")
    assert w.write_file(xlsx_path)
    wb = load_workbook(xlsx_path)
    assert wb.active["A1"].value == "Name"
    assert str(wb.active["B2"].value) == "1234567890123456"
    wb.close()
s.clearContents()
s.setRowCount(3)
s.setColumnCount(1)
s.write_cell(0, 0, "B")
s.write_cell(1, 0, "A")
s.write_cell(2, 0, "A")
w.sort_ascending()
assert s.text_at(0, 0) == "A"
w.highlight_duplicates()
assert s.item(0, 0).background().color().name() == "#ffe6a8"
w.clear_duplicate_highlights()
assert s.item(0, 0).background().color().name() == "#ffffff"
w.dirty = False
w.close()
print("Spreadsheet export, numeric text, sorting, and duplicate tests passed")
