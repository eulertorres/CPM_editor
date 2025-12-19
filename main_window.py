import sys
from typing import List

from PyQt6 import QtCore, QtGui, QtWidgets

from json_merger import JSONMergerLogic


class JSONMergerWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.logic = JSONMergerLogic()
        self.search_results: list[QtWidgets.QTreeWidgetItem] = []
        self.search_index = 0
        self.last_search_scope: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("CPM Project JSON Merger")
        self.resize(900, 650)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        top_button_row = QtWidgets.QHBoxLayout()
        layout.addLayout(top_button_row)

        self.btn_project1 = QtWidgets.QPushButton("Carregar Projeto 1")
        self.btn_project1.clicked.connect(self.load_project1)
        top_button_row.addWidget(self.btn_project1)

        self.btn_project2 = QtWidgets.QPushButton("Carregar Projeto 2")
        self.btn_project2.clicked.connect(self.load_project2)
        top_button_row.addWidget(self.btn_project2)

        self.btn_save = QtWidgets.QPushButton("Salvar Projeto 2")
        self.btn_save.clicked.connect(self.save_project2)
        top_button_row.addWidget(self.btn_save)

        self.btn_save_as = QtWidgets.QPushButton("Salvar como...")
        self.btn_save_as.clicked.connect(self.save_project2_as)
        top_button_row.addWidget(self.btn_save_as)

        # --- Barra de ferramentas: espaçamento e margens corretos (não sobrescrever tools_row)
        tools_row = QtWidgets.QHBoxLayout()
        tools_row.setSpacing(4)
        tools_row.setContentsMargins(4, 2, 4, 2)
        layout.addLayout(tools_row)

        tools_row.addWidget(self._create_tool_button("🔍", "Pesquisar", self.open_search_dialog))
        tools_row.addWidget(self._create_tool_button("✥", "Mover textura / Ajustar UV", self.open_uv_dialog))
        tools_row.addWidget(self._create_tool_button("📄", "Copiar", self.copy_element))
        tools_row.addWidget(self._create_tool_button("📋", "Colar", self.paste_element))
        tools_row.addWidget(self._create_tool_button("+Movment", "Gerar hierarquia +Movment", self.open_movement_dialog))

        splitter = QtWidgets.QSplitter()
        layout.addWidget(splitter, 1)

        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.addWidget(QtWidgets.QLabel("JSON 1"))
        self.tree1 = QtWidgets.QTreeWidget()
        self.tree1.setHeaderHidden(True)
        self.tree1.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree1.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.tree1, pos)
        )
        left_layout.addWidget(self.tree1)
        splitter.addWidget(left_panel)

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.addWidget(QtWidgets.QLabel("JSON 2"))
        self.tree2 = QtWidgets.QTreeWidget()
        self.tree2.setHeaderHidden(True)
        self.tree2.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree2.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.tree2, pos)
        )
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

    def save_project2_as(self) -> None:
        default_dir = None
        if self.logic.project2_path:
            default_dir = str(QtCore.QFileInfo(self.logic.project2_path).absolutePath())
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Salvar Projeto 2 como",
            directory=default_dir,
            filter="CPM Project (*.cpmproject)",
        )
        if not path:
            return
        if not path.lower().endswith(".cpmproject"):
            path = f"{path}.cpmproject"
        try:
            self.logic.save_project2_as(path)
            QtWidgets.QMessageBox.information(self, "Sucesso", "Projeto 2 salvo no novo local!")
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

    def shift_uv(self, du: int, dv: int) -> bool:
        selected = self.tree2.currentItem()
        if not selected:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione elemento em JSON 2 para ajustar UV")
            return False
        element = self.logic.get_by_path(self.logic.json2, self._item_path(selected))
        self.logic.adjust_uv(element, du, dv)
        self._build_tree(self.tree2, self.logic.json2)
        QtWidgets.QMessageBox.information(self, "Sucesso", f"UV ajustado em dU={du}, dV={dv}")
        return True

    def perform_search(self, query: str, scope: str) -> None:
        query = query.strip().lower()
        if not query:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Digite algo para buscar")
            return
        tree = self.tree1 if scope == "JSON 1" else self.tree2
        self.search_results = [
            item for item in self._walk_items(tree) if query in item.text(0).lower()
        ]
        if not self.search_results:
            QtWidgets.QMessageBox.information(self, "Busca", "Nada encontrado")
            return
        self.search_index = 0
        self.last_search_scope = scope
        self._highlight(tree, self.search_results[0])

    def next_search(self) -> None:
        if not self.search_results:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum resultado")
            return
        tree = self.tree1 if self.last_search_scope == "JSON 1" else self.tree2
        self.search_index = (self.search_index + 1) % len(self.search_results)
        self._highlight(tree, self.search_results[self.search_index])

    def clear_search(self) -> None:
        self.search_results = []
        self.search_index = 0
        self.last_search_scope = None

    def _build_tree(self, tree: QtWidgets.QTreeWidget, data: object) -> None:
        tree.clear()
        root = QtWidgets.QTreeWidgetItem(["root"])
        root.setData(0, QtCore.Qt.ItemDataRole.UserRole, [])
        root.setForeground(0, QtGui.QBrush(QtGui.QColor("#5c5c5c")))
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
                item.setForeground(0, QtGui.QBrush(QtGui.QColor("#7a7a7a")))
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
                if isinstance(element, dict):
                    item.setForeground(0, QtGui.QBrush(QtGui.QColor("#1b7fb3")))
                    font = item.font(0)
                    font.setBold(True)
                    item.setFont(0, font)
                else:
                    item.setForeground(0, QtGui.QBrush(QtGui.QColor("#5c5c5c")))
                parent.addChild(item)
                self._insert_items(tree, item, element, path + [idx])
        else:
            item = QtWidgets.QTreeWidgetItem([repr(value)])
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, path)
            item.setForeground(0, QtGui.QBrush(QtGui.QColor("#5c5c5c")))
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

    def _show_context_menu(self, tree: QtWidgets.QTreeWidget, pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        global_pos = tree.viewport().mapToGlobal(pos)

        if tree is self.tree1:
            copy_action = menu.addAction("Copiar de JSON 1")
            copy_action.triggered.connect(self.copy_element)
        else:
            move_action = menu.addAction("Mover de JSON 2")
            move_action.triggered.connect(self.move_element)
            paste_action = menu.addAction("Colar em JSON 2")
            paste_action.triggered.connect(self.paste_element)

        menu.exec(global_pos)

    def _create_tool_button(self, text: str, tooltip: str, slot: object) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setAutoRaise(True)

        # --- Ícone (texto) maior + botão compacto
        font = button.font()
        font.setPointSize(14)
        button.setFont(font)

        button.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        button.clicked.connect(slot)
        return button

    def open_search_dialog(self) -> None:
        dialog = SearchDialog(self)
        dialog.exec()

    def open_uv_dialog(self) -> None:
        dialog = UVShiftDialog(self)
        dialog.exec()

    def open_movement_dialog(self) -> None:
        if not self.logic.json2:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Carregue o Projeto 2 para usar o +Movment")
            return
        dialog = MovementDialog(self, self.logic)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._build_tree(self.tree2, self.logic.json2)


class SearchDialog(QtWidgets.QDialog):
    def __init__(self, parent: JSONMergerWindow) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Buscar")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        self.query_input = QtWidgets.QLineEdit()
        form.addRow("Termo", self.query_input)

        self.scope_combo = QtWidgets.QComboBox()
        self.scope_combo.addItems(["JSON 1", "JSON 2"])
        form.addRow("Onde buscar", self.scope_combo)
        layout.addLayout(form)

        buttons = QtWidgets.QHBoxLayout()
        btn_search = QtWidgets.QPushButton("Buscar")
        btn_search.clicked.connect(self._run_search)
        buttons.addWidget(btn_search)

        self.btn_next = QtWidgets.QPushButton("Próximo")
        self.btn_next.clicked.connect(self.parent_window.next_search)
        buttons.addWidget(self.btn_next)

        close_btn = QtWidgets.QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)

        layout.addLayout(buttons)

    def _run_search(self) -> None:
        self.parent_window.perform_search(self.query_input.text(), self.scope_combo.currentText())


class UVShiftDialog(QtWidgets.QDialog):
    def __init__(self, parent: JSONMergerWindow) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Mover textura (Shift UV)")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        self.du_input = QtWidgets.QSpinBox()
        self.du_input.setRange(-9999, 9999)
        self.du_input.setValue(0)
        form.addRow("dU", self.du_input)

        self.dv_input = QtWidgets.QSpinBox()
        self.dv_input.setRange(-9999, 9999)
        self.dv_input.setValue(0)
        form.addRow("dV", self.dv_input)

        layout.addLayout(form)

        buttons = QtWidgets.QHBoxLayout()
        btn_apply = QtWidgets.QPushButton("Aplicar")
        btn_apply.clicked.connect(self._apply_shift)
        buttons.addWidget(btn_apply)

        close_btn = QtWidgets.QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)

        layout.addLayout(buttons)

    def _apply_shift(self) -> None:
        du = int(self.du_input.value())
        dv = int(self.dv_input.value())
        if self.parent_window.shift_uv(du, dv):
            self.accept()


class MovementDialog(QtWidgets.QDialog):
    def __init__(self, parent: JSONMergerWindow, logic: JSONMergerLogic) -> None:
        super().__init__(parent)
        self.logic = logic
        self.setWindowTitle("+Movment")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        options = self.logic.list_elements()
        if not options:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum elemento encontrado em JSON 2")
            self.reject()
            return

        form = QtWidgets.QFormLayout()
        self.combos: dict[str, QtWidgets.QComboBox] = {}
        labels = [
            ("left_arm", "Braço esquerdo"),
            ("right_arm", "Braço direito"),
            ("left_leg", "Perna esquerda"),
            ("right_leg", "Perna direita"),
            ("left_sleeve", "Manga esquerda"),
            ("right_sleeve", "Manga direita"),
            ("left_pants", "Calça esquerda"),
            ("right_pants", "Calça direita"),
        ]
        for key, label in labels:
            combo = QtWidgets.QComboBox()
            for name, path in options:
                combo.addItem(name, userData=path)
            form.addRow(label, combo)
            self.combos[key] = combo
        layout.addLayout(form)

        buttons = QtWidgets.QHBoxLayout()
        apply_btn = QtWidgets.QPushButton("Aplicar")
        apply_btn.clicked.connect(self._run_tool)
        buttons.addWidget(apply_btn)

        cancel_btn = QtWidgets.QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def _run_tool(self) -> None:
        selection: dict[str, List[int | str]] = {}
        for key, combo in self.combos.items():
            data = combo.currentData()
            if data is None:
                QtWidgets.QMessageBox.warning(self, "Aviso", f"Selecione um valor para {key}")
                return
            selection[key] = list(data)
        if len({tuple(path) for path in selection.values()}) != len(selection):
            QtWidgets.QMessageBox.warning(self, "Aviso", "Cada seleção deve apontar para um elemento diferente.")
            return
        try:
            self.logic.apply_movement_tool(selection)
            QtWidgets.QMessageBox.information(self, "Sucesso", "Ferramenta +Movment aplicada.")
            self.accept()
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao aplicar +Movment:\n{exc}")


def run_app() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = JSONMergerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
