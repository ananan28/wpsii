import csv
import os
import sys
import secrets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QToolBar, QFileDialog, QMessageBox,
    QLineEdit, QLabel, QInputDialog, QFontDialog, QColorDialog, QComboBox,
    QStatusBar, QHeaderView
)

INITIAL_ROWS = 200
INITIAL_COLS = 26
MAX_VISIBLE_ROWS = 100000
MAX_VISIBLE_COLS = 16384

def col_name(i):
    s = ""
    i += 1
    while i:
        i, remainder = divmod(i - 1, 26)
        s = chr(65 + remainder) + s
    return s

class Sheet(QTableWidget):
    def __init__(self, name="Sheet1", rows=INITIAL_ROWS, cols=INITIAL_COLS):
        super().__init__(rows, cols)
        self.setObjectName(name)
        self.refresh_headers()
        self.verticalHeader().setDefaultSectionSize(26)
        self.horizontalHeader().setDefaultSectionSize(110)
        self.setAlternatingRowColors(False)
        self.setSelectionMode(QTableWidget.ContiguousSelection)
        self.setStyleSheet("QTableWidget { background: #ffffff; gridline-color: #dfe4e9; selection-background-color: #c9e6d6; selection-color: #16251d; } QHeaderView::section { background: #f1f3f5; border: 0; border-right: 1px solid #d6dbe0; border-bottom: 1px solid #d6dbe0; padding: 5px; color: #35434c; }")
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setMinimumSectionSize(25)
        self.verticalHeader().setMinimumSectionSize(18)
        self.verticalScrollBar().valueChanged.connect(self.grow_if_near_edge)
        self.horizontalScrollBar().valueChanged.connect(self.grow_if_near_edge)

    def grow_if_near_edge(self, *_):
        vs = self.verticalScrollBar()
        hs = self.horizontalScrollBar()
        if vs.maximum() and vs.value() >= vs.maximum() - 4 and self.rowCount() < MAX_VISIBLE_ROWS:
            self.setRowCount(min(MAX_VISIBLE_ROWS, self.rowCount() + 200))
        if hs.maximum() and hs.value() >= hs.maximum() - 2 and self.columnCount() < MAX_VISIBLE_COLS:
            self.setColumnCount(min(MAX_VISIBLE_COLS, self.columnCount() + 26))
            self.refresh_headers()

    def refresh_headers(self):
        self.setHorizontalHeaderLabels([col_name(i) for i in range(self.columnCount())])

    def ensure_size(self, rows, cols):
        if rows > MAX_VISIBLE_ROWS or cols > MAX_VISIBLE_COLS:
            raise ValueError(f"当前版本编辑上限为 {MAX_VISIBLE_ROWS} 行、{MAX_VISIBLE_COLS} 列，请拆分文件处理")
        if rows > self.rowCount():
            self.setRowCount(rows)
        if cols > self.columnCount():
            self.setColumnCount(cols)
            self.refresh_headers()

    def used_size(self):
        max_row = max_col = 0
        for item in self.findItems("", Qt.MatchContains):
            if item is not None and item.text():
                max_row = max(max_row, item.row() + 1)
                max_col = max(max_col, item.column() + 1)
        return max_row, max_col

    def populated_cells(self):
        for item in self.findItems("", Qt.MatchContains):
            if item is not None and item.text():
                yield item.row(), item.column(), item.text()

    def text_at(self, row, col):
        item = self.item(row, col)
        return item.text() if item else ""

    def write_cell(self, row, col, value):
        if value is None:
            return
        self.setItem(row, col, QTableWidgetItem(str(value)))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("海拓表格 1.4.1 — 未命名")
        self.resize(1450, 850)
        self.path = None
        self.dirty = False
        self.loading = False
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.currentChanged.connect(self.sync_formula)
        self.tabs.tabCloseRequested.connect(self.close_sheet)
        self.tabs.setStyleSheet("QTabBar::tab { padding: 9px 22px; background: #ebf1ec; color: #254031; } QTabBar::tab:selected { background: white; border-bottom: 2px solid #16834e; }")
        self.formula = QLineEdit()
        self.formula.setPlaceholderText("输入单元格内容或公式，例如 =SUM(A1:A10)")
        self.formula.returnPressed.connect(self.apply_formula)
        self.position = QLabel("A1")
        self.position.setMinimumWidth(70)
        self.search = QLineEdit()
        self.search.setPlaceholderText("查找内容")
        self.make_ui()
        self.add_sheet()
        self.statusBar().showMessage("准备就绪 · 双击单元格编辑，Ctrl+C / Ctrl+V 复制粘贴")
        self.setStyleSheet("""
            QMainWindow { background: #eef3f0; }
            QMenuBar { background: #174c37; color: white; padding: 8px; font-weight: 600; }
            QMenuBar::item:selected { background: #2b7353; border-radius: 5px; }
            QMenu { background: white; border: 1px solid #d6e2d9; padding: 6px; }
            QMenu::item:selected { background: #dff1e5; color: #10482e; }
            QToolBar { background: #fff; border-bottom: 1px solid #dce6de; spacing: 8px; padding: 13px; }
            QToolBar QToolButton { padding: 9px 12px; color: #195238; border-radius: 7px; font-weight: 600; }
            QToolBar QToolButton:hover { background: #e3f4e9; }
            QLineEdit { background: white; padding: 8px; border: 1px solid #d6e2d9; border-radius: 6px; }
            QTabWidget::pane { border: 1px solid #dce6de; background: white; }
            QStatusBar { background: #f7faf8; color: #406c53; }
        """)

    def make_ui(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("文件")
        edit_menu = menu.addMenu("编辑")
        data_menu = menu.addMenu("数据")
        format_menu = menu.addMenu("格式")
        def action(text, slot, shortcut=None, target=None):
            a = QAction(text, self)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            (target or file_menu).addAction(a)
            return a
        action("新建", self.new_document, "Ctrl+N")
        action("打开", self.open_file, "Ctrl+O")
        action("保存", self.save, "Ctrl+S")
        action("另存为", self.save_as, "Ctrl+Shift+S")
        action("复制", self.copy, "Ctrl+C", edit_menu)
        action("粘贴", self.paste, "Ctrl+V", edit_menu)
        action("剪切", self.cut, "Ctrl+X", edit_menu)
        action("查找", self.find_next, "Ctrl+F", edit_menu)
        action("批量查找替换", self.replace_all, "Ctrl+H", edit_menu)
        action("高亮重复项", self.highlight_duplicates, None, data_menu)
        action("取消重复项高亮", self.clear_duplicate_highlights, None, data_menu)
        action("随机填充选中区域", self.random_fill, None, data_menu)
        action("新增工作表", self.add_sheet, "Shift+F11", data_menu)
        action("插入行", self.insert_row, None, data_menu)
        action("删除行", self.delete_row, None, data_menu)
        action("按当前列去重", self.dedupe, None, data_menu)
        action("按选中列升序排序", self.sort_ascending, None, data_menu)
        action("按选中列降序排序", self.sort_descending, None, data_menu)
        action("按选中列筛选", self.filter_column, None, data_menu)
        action("清除筛选", self.clear_filters, None, data_menu)
        action("自动调整列宽", self.fit_columns, None, format_menu)
        action("设置当前列宽", self.set_column_width, None, format_menu)
        action("设置当前行高", self.set_row_height, None, format_menu)
        action("增加 200 行", self.add_rows, None, data_menu)
        action("增加 26 列", self.add_columns, None, data_menu)
        action("字体", self.choose_font, None, format_menu)
        action("填充颜色", self.fill_color, None, format_menu)
        action("加粗", self.bold, "Ctrl+B", format_menu)

        bar = QToolBar("功能区")
        bar.setMovable(False)
        self.addToolBar(bar)
        for label, func in [
            ("新建", self.new_document), ("打开", self.open_file), ("保存", self.save),
            ("复制", self.copy), ("粘贴", self.paste), ("加粗", self.bold),
            ("字体", self.choose_font), ("填充色", self.fill_color),
            ("插入行", self.insert_row), ("删除行", self.delete_row),
            ("新增工作表", self.add_sheet), ("升序 A→Z", self.sort_ascending),
            ("降序 Z→A", self.sort_descending), ("筛选", self.filter_column),
            ("清除筛选", self.clear_filters), ("自动列宽", self.fit_columns),
            ("列宽", self.set_column_width), ("行高", self.set_row_height),
            ("增加行", self.add_rows), ("增加列", self.add_columns),
            ("去重", self.dedupe), ("重复项", self.highlight_duplicates),
            ("替换", self.replace_all), ("随机填充", self.random_fill)
        ]:
            bar.addAction(label, func)
        bar.addSeparator()
        bar.addWidget(self.search)
        bar.addAction("查找下一个", self.find_next)

        main = QWidget()
        layout = QVBoxLayout(main)
        layout.setContentsMargins(6, 6, 6, 6)
        formula_line = QHBoxLayout()
        formula_line.addWidget(QLabel("单元格"))
        formula_line.addWidget(self.position)
        formula_line.addWidget(QLabel("fx"))
        formula_line.addWidget(self.formula)
        layout.addLayout(formula_line)
        layout.addWidget(self.tabs)
        self.setCentralWidget(main)

    def sheet(self):
        return self.tabs.currentWidget()

    def add_sheet(self):
        name = f"工作表{self.tabs.count() + 1}"
        sheet = Sheet(name)
        sheet.currentCellChanged.connect(self.sync_formula)
        sheet.itemChanged.connect(self.mark_dirty)
        sheet.itemSelectionChanged.connect(self.sync_formula)
        self.tabs.addTab(sheet, name)
        self.tabs.setCurrentWidget(sheet)
        return sheet

    def close_sheet(self, index):
        if self.tabs.count() <= 1:
            QMessageBox.information(self, "提示", "至少保留一个工作表")
            return
        self.tabs.removeTab(index)
        self.dirty = True

    def mark_dirty(self, *_):
        if not self.loading:
            self.dirty = True
        self.sync_formula()

    def sync_formula(self, *_):
        sheet = self.sheet()
        if not sheet:
            return
        row = max(0, sheet.currentRow())
        col = max(0, sheet.currentColumn())
        self.position.setText(f"{col_name(col)}{row + 1}")
        self.formula.blockSignals(True)
        self.formula.setText(sheet.text_at(row, col))
        self.formula.blockSignals(False)

    def apply_formula(self):
        sheet = self.sheet()
        if not sheet:
            return
        row = max(0, sheet.currentRow())
        col = max(0, sheet.currentColumn())
        sheet.write_cell(row, col, self.formula.text())

    def selection_bounds(self):
        sheet = self.sheet()
        ranges = sheet.selectedRanges()
        if not ranges:
            return None
        r = ranges[0]
        return r.topRow(), r.leftColumn(), r.bottomRow(), r.rightColumn()

    def copy(self):
        bounds = self.selection_bounds()
        if bounds is None:
            return
        r1, c1, r2, c2 = bounds
        sheet = self.sheet()
        out = []
        for r in range(r1, r2 + 1):
            out.append("\t".join(sheet.text_at(r, c).replace("\t", " ").replace("\n", " ") for c in range(c1, c2 + 1)))
        QApplication.clipboard().setText("\n".join(out))

    def cut(self):
        self.copy()
        bounds = self.selection_bounds()
        if bounds:
            r1, c1, r2, c2 = bounds
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    self.sheet().write_cell(r, c, "")

    def paste(self):
        sheet = self.sheet()
        if not sheet:
            return
        text = QApplication.clipboard().text()
        data = [line.split("\t") for line in text.splitlines()]
        if not data:
            return
        r0 = max(0, sheet.currentRow())
        c0 = max(0, sheet.currentColumn())
        try:
            sheet.ensure_size(r0 + len(data), c0 + max(map(len, data)))
        except ValueError as e:
            QMessageBox.warning(self, "超出限制", str(e))
            return
        sheet.setUpdatesEnabled(False)
        try:
            for i, row in enumerate(data):
                for j, value in enumerate(row):
                    sheet.write_cell(r0 + i, c0 + j, value)
        finally:
            sheet.setUpdatesEnabled(True)

    def insert_row(self):
        sheet = self.sheet()
        if sheet.rowCount() >= MAX_VISIBLE_ROWS:
            return
        sheet.insertRow(max(0, sheet.currentRow()))
        self.dirty = True

    def delete_row(self):
        sheet = self.sheet()
        if sheet.rowCount() > 1:
            sheet.removeRow(max(0, sheet.currentRow()))
            self.dirty = True

    def chosen_items(self):
        return self.sheet().selectedItems()

    def bold(self):
        for item in self.chosen_items():
            font = item.font()
            font.setBold(not font.bold())
            item.setFont(font)

    def choose_font(self):
        font, ok = QFontDialog.getFont(self)
        if ok:
            for item in self.chosen_items():
                item.setFont(font)

    def fill_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            for item in self.chosen_items():
                item.setBackground(color)

    def find_next(self):
        needle = self.search.text()
        if not needle:
            self.search.setFocus()
            return
        sheet = self.sheet()
        start = max(0, sheet.currentRow() * sheet.columnCount() + sheet.currentColumn() + 1)
        total = sheet.rowCount() * sheet.columnCount()
        hits = sorted((r * sheet.columnCount() + c, r, c) for r, c, value in sheet.populated_cells() if needle.casefold() in value.casefold())
        for _, r, c in sorted(hits, key=lambda x: (x[0] < start, x[0])):
            sheet.setCurrentCell(r, c)
            sheet.scrollToItem(sheet.item(r, c))
            return
        QMessageBox.information(self, "查找", "没有找到匹配的内容")

    def sort_ascending(self):
        self.sort_column(Qt.AscendingOrder)

    def sort_descending(self):
        self.sort_column(Qt.DescendingOrder)

    def sort_column(self, direction):
        sheet = self.sheet()
        col = max(0, sheet.currentColumn())
        sheet.setSortingEnabled(False)
        sheet.sortItems(col, direction)
        self.dirty = True
        self.statusBar().showMessage(f"已按 {col_name(col)} 列排序")

    def filter_column(self):
        sheet = self.sheet()
        col = max(0, sheet.currentColumn())
        criterion, ok = QInputDialog.getText(self, "筛选", f"仅显示 {col_name(col)} 列包含以下文字的行（留空显示全部）：")
        if not ok:
            return
        match = criterion.strip().casefold()
        visible = 0
        for row in range(sheet.rowCount()):
            show = (not match) or match in sheet.text_at(row, col).casefold()
            sheet.setRowHidden(row, not show)
            if show:
                visible += 1
        self.statusBar().showMessage(f"筛选完成：显示 {visible} 行")

    def clear_filters(self):
        sheet = self.sheet()
        for row in range(sheet.rowCount()):
            sheet.setRowHidden(row, False)
        self.statusBar().showMessage("已清除筛选")

    def fit_columns(self):
        sheet = self.sheet()
        sheet.resizeColumnsToContents()
        self.statusBar().showMessage("已自动调整列宽")

    def set_column_width(self):
        sheet = self.sheet()
        col = max(0, sheet.currentColumn())
        size, ok = QInputDialog.getInt(self, "设置列宽", f"{col_name(col)} 列宽度（像素）", sheet.columnWidth(col), 25, 1500)
        if ok:
            sheet.setColumnWidth(col, size)
            self.dirty = True

    def set_row_height(self):
        sheet = self.sheet()
        row = max(0, sheet.currentRow())
        size, ok = QInputDialog.getInt(self, "设置行高", f"第 {row + 1} 行高度（像素）", sheet.rowHeight(row), 18, 1000)
        if ok:
            sheet.setRowHeight(row, size)
            self.dirty = True

    def add_rows(self):
        sheet = self.sheet()
        sheet.setRowCount(min(MAX_VISIBLE_ROWS, sheet.rowCount() + 200))

    def add_columns(self):
        sheet = self.sheet()
        sheet.setColumnCount(min(MAX_VISIBLE_COLS, sheet.columnCount() + 26))
        sheet.refresh_headers()

    def select_column(self):
        self.sheet().selectColumn(max(0, self.sheet().currentColumn()))


    def replace_all(self):
        sheet = self.sheet()
        target, ok = QInputDialog.getText(self, "批量替换", "查找文字（区分大小写）：")
        if not ok or not target:
            return
        replacement, ok = QInputDialog.getText(self, "批量替换", "替换为（可留空）：")
        if not ok:
            return
        candidates = self.chosen_items() if self.chosen_items() else list(sheet.findItems(target, Qt.MatchContains))
        affected = 0
        for item in candidates:
            old = item.text()
            if target in old:
                item.setText(old.replace(target, replacement))
                affected += 1
        self.statusBar().showMessage(f"已替换 {affected} 个单元格")
        QMessageBox.information(self, "替换完成", f"已修改 {affected} 个单元格。")

    def highlight_duplicates(self):
        sheet = self.sheet()
        column = max(0, sheet.currentColumn())
        seen = {}
        duplicates = []
        for row in range(sheet.rowCount()):
            key = sheet.text_at(row, column).strip().casefold()
            if not key:
                continue
            if key in seen:
                duplicates.append(seen[key])
                duplicates.append(row)
            else:
                seen[key] = row
        color = QColor("#ffe6a8")
        for row in set(duplicates):
            item = sheet.item(row, column)
            if item:
                item.setBackground(color)
        self.dirty = bool(duplicates) or self.dirty
        self.statusBar().showMessage(f"{col_name(column)} 列发现 {len(set(duplicates))} 个重复值单元格（包含首次出现）")

    def clear_duplicate_highlights(self):
        sheet = self.sheet()
        col = max(0, sheet.currentColumn())
        for row in range(sheet.rowCount()):
            item = sheet.item(row, col)
            if item:
                item.setBackground(QColor("white"))
        self.dirty = True

    def random_fill(self):
        sheet = self.sheet()
        bounds = self.selection_bounds()
        if not bounds:
            QMessageBox.information(self, "随机填充", "请先选择需要填充的区域")
            return
        r1, c1, r2, c2 = bounds
        if (r2-r1+1)*(c2-c1+1)>100000:
            QMessageBox.warning(self, "随机填充", "每次最多填充 100,000 个单元格")
            return
        low, ok = QInputDialog.getInt(self, "随机填充", "随机整数下限", 1, -1000000000, 1000000000)
        if not ok:
            return
        high, ok = QInputDialog.getInt(self, "随机填充", "随机整数上限", 100, low, 1000000000)
        if not ok:
            return
        if QMessageBox.question(self, "确认覆盖", f"将用随机整数覆盖 {((r2-r1+1)*(c2-c1+1)):,} 个单元格，确定继续？") != QMessageBox.Yes:
            return
        sheet.setUpdatesEnabled(False)
        try:
            for row in range(r1, r2+1):
                for col in range(c1, c2+1):
                    sheet.write_cell(row, col, low + secrets.randbelow(high-low+1))
        finally:
            sheet.setUpdatesEnabled(True)
        self.dirty = True
        self.statusBar().showMessage("随机填充完成")

    def dedupe(self):
        sheet = self.sheet()
        col = max(0, sheet.currentColumn())
        ans = QMessageBox.question(self, "按列去重", f"按照 {col_name(col)} 列删除重复行（保留首条，空白不去重）？")
        if ans != QMessageBox.Yes:
            return
        seen = set()
        duplicate_rows = []
        for r in range(sheet.rowCount()):
            key = sheet.text_at(r, col).strip().casefold()
            if not key:
                continue
            if key in seen:
                duplicate_rows.append(r)
            else:
                seen.add(key)
        for r in reversed(duplicate_rows):
            sheet.removeRow(r)
        deleted = len(duplicate_rows)
        QMessageBox.information(self, "完成", f"删除了 {deleted} 行。注意：去重以当前列为依据。")
        self.dirty = True

    def maybe_save(self):
        if not self.dirty:
            return True
        answer = QMessageBox.question(self, "未保存更改", "当前文件有未保存的修改，是否保存？",
                                      QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if answer == QMessageBox.Cancel:
            return False
        if answer == QMessageBox.Save:
            return self.save()
        return True

    def new_document(self):
        if not self.maybe_save():
            return
        self.tabs.clear()
        self.path = None
        self.dirty = False
        self.add_sheet()
        self.setWindowTitle("海拓表格 1.4.1 — 未命名")

    def open_file(self):
        if not self.maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(self, "打开表格", "", "表格文件 (*.xlsx *.csv *.tsv *.txt);;所有文件 (*)")
        if not path:
            return
        try:
            ext = os.path.splitext(path)[1].lower()
            self.loading = True
            self.tabs.clear()
            if ext == ".xlsx":
                from openpyxl import load_workbook
                wb = load_workbook(path, read_only=True, data_only=False)
                for ws in wb.worksheets:
                    if ws.max_row > MAX_VISIBLE_ROWS or ws.max_column > MAX_VISIBLE_COLS:
                        raise ValueError("文件超过当前版本编辑上限")
                    sheet = self.add_sheet()
                    self.tabs.setTabText(self.tabs.indexOf(sheet), ws.title)
                    sheet.setUpdatesEnabled(False)
                    sheet.ensure_size(max(1, ws.max_row), max(1, ws.max_column))
                    for row in ws.iter_rows():
                        for cell in row:
                            if cell.value is not None:
                                sheet.write_cell(cell.row - 1, cell.column - 1, cell.value)
                    sheet.setUpdatesEnabled(True)
                wb.close()
            else:
                delimiter = "\t" if ext in (".tsv", ".txt") else ","
                rows = None
                for encoding in ("utf-8-sig", "utf-8", "gb18030"):
                    try:
                        with open(path, encoding=encoding, newline="") as f:
                            rows = list(csv.reader(f, delimiter=delimiter))
                        break
                    except UnicodeDecodeError:
                        pass
                if rows is None:
                    raise ValueError("无法读取文件编码")
                if len(rows) > MAX_VISIBLE_ROWS or max((len(r) for r in rows), default=0) > MAX_VISIBLE_COLS:
                    raise ValueError("文件超过当前版本编辑上限")
                sheet = self.add_sheet()
                sheet.ensure_size(max(1, len(rows)), max((len(r) for r in rows), default=1))
                sheet.setUpdatesEnabled(False)
                for r, row in enumerate(rows):
                    for c, value in enumerate(row):
                        if value:
                            sheet.write_cell(r, c, value)
                sheet.setUpdatesEnabled(True)
            if not self.tabs.count():
                self.add_sheet()
            self.path = path
            self.dirty = False
            self.setWindowTitle("海拓表格 1.4.1 — " + os.path.basename(path))
            self.statusBar().showMessage("已打开：" + path)
        except Exception as e:
            QMessageBox.critical(self, "打开失败", str(e))
            if not self.tabs.count():
                self.add_sheet()
        finally:
            self.loading = False

    def save(self):
        if not self.path:
            return self.save_as()
        return self.write_file(self.path)

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存表格", "", "Excel 工作簿 (*.xlsx);;CSV (*.csv);;TSV (*.tsv)")
        if not path:
            return False
        return self.write_file(path)

    def write_file(self, path):
        try:
            if path.lower().endswith(".xlsx"):
                from openpyxl import Workbook
                from openpyxl.styles import Font, PatternFill, Alignment
                wb = Workbook()
                wb.remove(wb.active)
                for i in range(self.tabs.count()):
                    sheet = self.tabs.widget(i)
                    ws = wb.create_sheet(self.tabs.tabText(i))
                    for row, col, value in sheet.populated_cells():
                        cell = ws.cell(row + 1, col + 1, value)
                        item = sheet.item(row, col)
                        if item.font().bold():
                            cell.font = Font(bold=True)
                        bg = item.background().color()
                        if bg.isValid() and bg.alpha() > 0 and bg.name() != "#ffffff":
                            cell.fill = PatternFill(fill_type="solid", fgColor=bg.name().lstrip("#").upper())
                    for col in range(min(sheet.columnCount(), 256)):
                        from openpyxl.utils import get_column_letter
                        if sheet.columnWidth(col) != 110:
                            ws.column_dimensions[get_column_letter(col + 1)].width = max(3, sheet.columnWidth(col) / 7)
                    for row in range(min(sheet.rowCount(), 5000)):
                        if sheet.rowHeight(row) != 26:
                            ws.row_dimensions[row + 1].height = sheet.rowHeight(row) * 0.75
                wb.save(path)
            else:
                sheet = self.sheet()
                if self.tabs.count() > 1:
                    if QMessageBox.question(self, "CSV 仅支持单表", "CSV 只能保存当前工作表，是否继续？") != QMessageBox.Yes:
                        return False
                delimiter = "\\t" if path.lower().endswith(".tsv") else ","
                used_rows, used_cols = sheet.used_size()
                with open(path, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f, delimiter=delimiter)
                    for r in range(used_rows):
                        writer.writerow([sheet.text_at(r, col) for col in range(used_cols)])
            self.path = path
            self.dirty = False
            self.setWindowTitle("海拓表格 1.4.1 — " + os.path.basename(path))
            self.statusBar().showMessage("已保存：" + path)
            return True
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return False

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
