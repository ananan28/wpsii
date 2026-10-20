import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from haituo_qt import MainWindow
app = QApplication([])
w = MainWindow()
s = w.sheet()
s.write_cell(0,0,"B")
s.write_cell(1,0,"A")
s.write_cell(2,0,"A")
w.sort_ascending()
assert s.text_at(0,0) == "A"
w.highlight_duplicates()
assert s.item(0,0).background().color().name() == "#ffe6a8"
assert s.item(1,0).background().color().name() == "#ffe6a8"
w.clear_duplicate_highlights()
assert s.item(0,0).background().color().name() == "#ffffff"
w.close()
print("Basic UI sorting and duplicate highlighting smoke tests passed")
