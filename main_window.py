import sys
from typing import List

from PyQt6 import QtCore, QtWidgets

from json_merger import JSONMergerLogic


class JSONMergerWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.logic = JSONMergerLogic()
        self.search_results: list[QtWidgets.QTreeWidgetItem] = []
        self.search_index = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("CPM Project JSON Merger")
        self.resize(900, 650)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        button_row = QtWidgets.QHBoxLayout()
        layout.addLayout(button_row)

        self.btn_project1 = QtWidgets.QPushButton("Carregar Projeto 1")
        self.btn_project1.clicked.connect(self.load_project1)
        button_row.addWidget(self.btn_project1)

        self.btn_project2 = QtWidgets.QPushButton("Carregar Projeto 2")
        self.btn_project2.clicked.connect(self.load_project2)
        button_row.addWidget(self.btn_project2)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Buscar...")
        button_row.addWidget(self.search_input)

        self.search_scope = QtWidgets.QComboBox()
        self.search_scope.addItems(["JSON 1", "JSON 2"])
        button_row.addWidget(self.search_scope)

        self.btn_search = QtWidgets.QPushButton("Buscar")
        self.btn_search.clicked.connect(self.search)
        button_row.addWidget(self.btn_search)

        self.btn_next_search = QtWidgets.QPushButton("Próximo")
        self.btn_next_search.clicked.connect(self.next_search)
        button_row.addWidget(self.btn_next_search)

        self.btn_copy = QtWidgets.QPushButton("Copiar")
        self.btn_copy.clicked.connect(self.copy_element)
        button_row.addWidget(self.btn_copy)

        self.btn_move = QtWidgets.QPushButton("Mover")
        self.btn_move.clicked.connect(self.move_element)
        button_row.addWidget(self.btn_move)

        self.btn_paste = QtWidgets.QPushButton("Colar")
        self.btn_paste.clicked.connect(self.paste_element)
        button_row.addWidget(self.btn_paste)

        self.du_input = QtWidgets.QLineEdit("0")
        self.du_input.setFixedWidth(60)
        self.dv_input = QtWidgets.QLineEdit("0")
        self.dv_input.setFixedWidth(60)

        button_row.addWidget(QtWidgets.QLabel("dU:"))
        button_row.addWidget(self.du_input)
        button_row.addWidget(QtWidgets.QLabel("dV:"))
        button_row.addWidget(self.dv_input)

        self.btn_shift_uv = QtWidgets.QPushButton("Shift UV")
        self.btn_shift_uv.clicked.connect(self.shift_uv)
        button_row.addWidget(self.btn_shift_uv)

        self.btn_save = QtWidgets.QPushButton("Salvar Projeto 2")
        self.btn_save.clicked.connect(self.save_project2)
        button_row.addWidget(self.btn_save)

        splitter = QtWidgets.QSplitter()
        layout.addWidget(splitter, 1)

        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.addWidget(QtWidgets.QLabel("JSON 1"))
        self.tree1 = QtWidgets.QTreeWidget()
        self.tree1.setHeaderHidden(True)
        left_layout.addWidget(self.tree1)
        splitter.addWidget(left_panel)

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.addWidget(QtWidgets.QLabel("JSON 2"))
        self.tree2 = QtWidgets.QTreeWidget()
        self.tree2.setHeaderHidden(True)
        right_layout.addWidget(self.tree2)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(central)

    def load_project1(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Selecione o .cpmproject", filter="CPM Project (*.cpmproject)"
        )
        if not path:
            return
        try:
            self.logic.load_project1(path)
            self._build_tree(self.tree1, self.logic.json1)
            self.clear_search()
            self.logic.clear_clipboard()
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar Projeto 1:\n{exc}")

    def load_project2(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Selecione o .cpmproject", filter="CPM Project (*.cpmproject)"
        )
        if not path:
            return
        try:
            self.logic.load_project2(path)
            self._build_tree(self.tree2, self.logic.json2)
            self.clear_search()
            self.logic.clear_clipboard()
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar Projeto 2:\n{exc}")

    def save_project2(self) -> None:
        try:
            self.logic.save_project2()
            QtWidgets.QMessageBox.information(self, "Sucesso", "Projeto 2 atualizado com sucesso!")
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao salvar Projeto 2:\n{exc}")

    def copy_element(self) -> None:
        selected = self.tree1.currentItem()
        if not selected:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione algo em JSON 1")
            return
        path = self._item_path(selected)
        self.logic.copy_from_json1(path)
        QtWidgets.QMessageBox.information(self, "Clipboard", "Elemento copiado")

    def move_element(self) -> None:
        selected = self.tree2.currentItem()
        if not selected:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione algo em JSON 2 para mover")
            return
        path = self._item_path(selected)
        self.logic.move_from_json2(path)
        QtWidgets.QMessageBox.information(
            self,
            "Clipboard",
            "Elemento marcado para mover. Agora selecione destino e clique Colar",
        )

    def paste_element(self) -> None:
        if self.logic.clipboard is None:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Clipboard vazio")
            return
        selected = self.tree2.currentItem()
        if not selected:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione destino em JSON 2")
            return
        dest_path = self._item_path(selected)
        try:
            self.logic.paste_to_json2(dest_path)
            self._build_tree(self.tree2, self.logic.json2)
            QtWidgets.QMessageBox.information(self, "Sucesso", "Elemento colado")
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao colar elemento:\n{exc}")

    def shift_uv(self) -> None:
        try:
            du = int(self.du_input.text())
            dv = int(self.dv_input.text())
        except ValueError:
            QtWidgets.QMessageBox.critical(self, "Erro", "dU e dV devem ser inteiros")
            return
        selected = self.tree2.currentItem()
        if not selected:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione elemento em JSON 2 para ajustar UV")
            return
        element = self.logic.get_by_path(self.logic.json2, self._item_path(selected))
        self.logic.adjust_uv(element, du, dv)
        self._build_tree(self.tree2, self.logic.json2)
        QtWidgets.QMessageBox.information(self, "Sucesso", f"UV ajustado em dU={du}, dV={dv}")

    def search(self) -> None:
        query = self.search_input.text().strip().lower()
        if not query:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Digite algo para buscar")
            return
        tree = self.tree1 if self.search_scope.currentText() == "JSON 1" else self.tree2
        self.search_results = [item for item in self._walk_items(tree) if query in item.text(0).lower()]
        if not self.search_results:
            QtWidgets.QMessageBox.information(self, "Busca", "Nada encontrado")
            return
        self.search_index = 0
        self._highlight(tree, self.search_results[0])

    def next_search(self) -> None:
        if not self.search_results:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum resultado")
            return
        tree = self.tree1 if self.search_scope.currentText() == "JSON 1" else self.tree2
        self.search_index = (self.search_index + 1) % len(self.search_results)
        self._highlight(tree, self.search_results[self.search_index])

    def clear_search(self) -> None:
        self.search_results = []
        self.search_index = 0

    def _build_tree(self, tree: QtWidgets.QTreeWidget, data: object) -> None:
        tree.clear()
        root = QtWidgets.QTreeWidgetItem(["root"])
        root.setData(0, QtCore.Qt.ItemDataRole.UserRole, [])
        tree.addTopLevelItem(root)
        self._insert_items(tree, root, data, [])
        tree.expandItem(root)

    def _insert_items(
        self,
        tree: QtWidgets.QTreeWidget,
        parent: QtWidgets.QTreeWidgetItem,
        value: object,
        path: List[int | str],
    ) -> None:
        if isinstance(value, dict):
            for key, val in value.items():
                item = QtWidgets.QTreeWidgetItem([str(key)])
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, path + [key])
                parent.addChild(item)
                self._insert_items(tree, item, val, path + [key])
        elif isinstance(value, list):
            for idx, element in enumerate(value):
                if isinstance(element, dict):
                    label = element.get("id") or element.get("name") or f"[{idx}]"
                else:
                    label = f"[{idx}]"
                item = QtWidgets.QTreeWidgetItem([label])
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, path + [idx])
                parent.addChild(item)
                self._insert_items(tree, item, element, path + [idx])
        else:
            item = QtWidgets.QTreeWidgetItem([repr(value)])
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, path)
            parent.addChild(item)

    def _highlight(self, tree: QtWidgets.QTreeWidget, item: QtWidgets.QTreeWidgetItem) -> None:
        ancestor = item.parent()
        while ancestor:
            tree.expandItem(ancestor)
            ancestor = ancestor.parent()
        tree.setCurrentItem(item)
        tree.scrollToItem(item)
        QtWidgets.QMessageBox.information(
            self,
            "Busca",
            f"Resultado {self.search_index + 1} de {len(self.search_results)}",
        )

    def _walk_items(self, tree: QtWidgets.QTreeWidget) -> List[QtWidgets.QTreeWidgetItem]:
        def walk(parent: QtWidgets.QTreeWidgetItem) -> List[QtWidgets.QTreeWidgetItem]:
            items: List[QtWidgets.QTreeWidgetItem] = []
            for index in range(parent.childCount()):
                child = parent.child(index)
                items.append(child)
                items.extend(walk(child))
            return items

        result: List[QtWidgets.QTreeWidgetItem] = []
        for idx in range(tree.topLevelItemCount()):
            top = tree.topLevelItem(idx)
            result.append(top)
            result.extend(walk(top))
        return result

    @staticmethod
    def _item_path(item: QtWidgets.QTreeWidgetItem) -> List[int | str]:
        data = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return list(data) if data is not None else []


def run_app() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = JSONMergerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
