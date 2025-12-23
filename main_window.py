import sys
from typing import Callable, List

from PyQt6 import QtCore, QtGui, QtWidgets

from json_merger import JSONMergerLogic


class StatusMixin:
    def _notify(self, message: str, level: str = "info") -> None:
        parent = self.parent() if hasattr(self, "parent") else None
        target = None
        if isinstance(self, QtWidgets.QMainWindow):
            target = self
        elif isinstance(parent, QtWidgets.QMainWindow):
            target = parent
        if target:
            colors = {"info": "#7a7a7a", "success": "#2e8b57", "warning": "#cc8800", "error": "#c0392b"}
            color = colors.get(level, "#7a7a7a")
            target.statusBar().setStyleSheet(f"QStatusBar{{color:{color}; padding:4px;}}")
            target.statusBar().showMessage(message, 6000)
        else:
            QtWidgets.QMessageBox.information(self, "Info", message)


class JSONMergerWindow(QtWidgets.QMainWindow, StatusMixin):
    def __init__(self) -> None:
        super().__init__()
        self.logic = JSONMergerLogic()
        self.search_results: list[QtWidgets.QTreeWidgetItem] = []
        self.search_index = 0
        self.last_search_scope: str | None = None
        self.show_only_elements = False
        self._setup_ui()
        self.statusBar().showMessage("Pronto")

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

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs, 1)

        # ----- Aba de Modelos
        models_tab = QtWidgets.QWidget()
        models_layout = QtWidgets.QVBoxLayout(models_tab)

        tools_row = QtWidgets.QHBoxLayout()
        tools_row.setSpacing(4)
        tools_row.setContentsMargins(4, 2, 4, 2)
        models_layout.addLayout(tools_row)

        tools_row.addWidget(self._create_tool_button("🔍", "Pesquisar", self.open_search_dialog))
        tools_row.addWidget(self._create_tool_button("✥", "Mover textura / Ajustar UV", self.open_uv_dialog))
        tools_row.addWidget(self._create_tool_button("📄", "Copiar", self.copy_element))
        tools_row.addWidget(self._create_tool_button("📋", "Colar", self.paste_element))
        tools_row.addWidget(self._create_tool_button("+Movment", "Gerar hierarquia +Movment", self.open_movement_dialog))
        tools_row.addWidget(self._create_tool_button("🎨", "Colorir hierarquia", self.colorize_hierarchy))

        self.elements_only_checkbox = QtWidgets.QCheckBox("apenas Elementos")
        self.elements_only_checkbox.stateChanged.connect(self._toggle_elements_only)
        models_layout.addWidget(self.elements_only_checkbox)

        splitter = QtWidgets.QSplitter()
        models_layout.addWidget(splitter, 1)

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

        self.tabs.addTab(models_tab, "Modelos")

        # ----- Aba de Animações
        animations_tab = QtWidgets.QWidget()
        anim_layout = QtWidgets.QVBoxLayout(animations_tab)

        anim_buttons = QtWidgets.QHBoxLayout()
        self.btn_copy_anim = QtWidgets.QPushButton("Copiar animação do Projeto 1")
        self.btn_copy_anim.clicked.connect(self.copy_animation)
        anim_buttons.addWidget(self.btn_copy_anim)

        self.btn_paste_anim = QtWidgets.QPushButton("Colar animação no Projeto 2")
        self.btn_paste_anim.clicked.connect(self.paste_animation)
        anim_buttons.addWidget(self.btn_paste_anim)

        self.btn_apply_frame = QtWidgets.QPushButton("Aplicar frame ao modelo")
        self.btn_apply_frame.clicked.connect(self.apply_frame_to_model)
        anim_buttons.addWidget(self.btn_apply_frame)

        anim_layout.addLayout(anim_buttons)

        anim_splitter = QtWidgets.QSplitter()
        anim_layout.addWidget(anim_splitter, 1)

        anim_left = QtWidgets.QWidget()
        anim_left_layout = QtWidgets.QVBoxLayout(anim_left)
        anim_left_layout.addWidget(QtWidgets.QLabel("Animações Projeto 1"))
        self.anim_list1 = QtWidgets.QListWidget()
        anim_left_layout.addWidget(self.anim_list1)
        anim_splitter.addWidget(anim_left)

        anim_right = QtWidgets.QWidget()
        anim_right_layout = QtWidgets.QVBoxLayout(anim_right)
        anim_right_layout.addWidget(QtWidgets.QLabel("Animações Projeto 2"))
        self.anim_list2 = QtWidgets.QListWidget()
        anim_right_layout.addWidget(self.anim_list2)
        anim_splitter.addWidget(anim_right)

        anim_splitter.setStretchFactor(0, 1)
        anim_splitter.setStretchFactor(1, 1)

        self.tabs.addTab(animations_tab, "Animações")

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
            self._refresh_animation_lists()
            self.clear_search()
            self.logic.clear_clipboard()
            self._notify("Projeto 1 carregado", "info")
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Falha ao carregar Projeto 1: {exc}", "error")

    def load_project2(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Selecione o .cpmproject", filter="CPM Project (*.cpmproject)"
        )
        if not path:
            return
        try:
            self.logic.load_project2(path)
            self._build_tree(self.tree2, self.logic.json2)
            self._refresh_animation_lists()
            self.clear_search()
            self.logic.clear_clipboard()
            self._notify("Projeto 2 carregado", "info")
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Falha ao carregar Projeto 2: {exc}", "error")

    def save_project2(self) -> None:
        try:
            self.logic.save_project2()
            self._notify("Projeto 2 atualizado com sucesso!", "success")
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Falha ao salvar Projeto 2: {exc}", "error")

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
            self._notify("Projeto 2 salvo no novo local!", "success")
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Falha ao salvar Projeto 2: {exc}", "error")

    def copy_element(self) -> None:
        selected = self.tree1.currentItem()
        if not selected:
            self._notify("Selecione algo em JSON 1", "warning")
            return
        path = self._item_path(selected)
        self.logic.copy_from_json1(path)
        self._notify("Elemento copiado do JSON 1", "info")

    def move_element(self) -> None:
        selected = self.tree2.currentItem()
        if not selected:
            self._notify("Selecione algo em JSON 2 para mover", "warning")
            return
        path = self._item_path(selected)
        self.logic.move_from_json2(path)
        self._notify("Elemento marcado para mover. Agora selecione destino e clique Colar", "info")

    def paste_element(self) -> None:
        if self.logic.clipboard is None:
            self._notify("Clipboard vazio", "warning")
            return
        selected = self.tree2.currentItem()
        if not selected:
            self._notify("Selecione destino em JSON 2", "warning")
            return
        dest_path = self._item_path(selected)
        try:
            self.logic.paste_to_json2(dest_path)
            self._build_tree(self.tree2, self.logic.json2)
            self._notify("Elemento colado", "success")
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Falha ao colar elemento: {exc}", "error")

    def shift_uv(self, du: int, dv: int) -> bool:
        selected = self.tree2.currentItem()
        if not selected:
            self._notify("Selecione elemento em JSON 2 para ajustar UV", "warning")
            return False
        element = self.logic.get_by_path(self.logic.json2, self._item_path(selected))
        self.logic.adjust_uv(element, du, dv)
        self._build_tree(self.tree2, self.logic.json2)
        self._notify(f"UV ajustado em dU={du}, dV={dv}", "success")
        return True

    def perform_search(self, query: str, scope: str) -> None:
        query = query.strip().lower()
        if not query:
            self._notify("Digite algo para buscar", "warning")
            return
        tree = self.tree1 if scope == "JSON 1" else self.tree2
        self.search_results = [
            item for item in self._walk_items(tree) if query in item.text(0).lower()
        ]
        if not self.search_results:
            self._notify("Nada encontrado", "info")
            return
        self.search_index = 0
        self.last_search_scope = scope
        self._highlight(tree, self.search_results[0])

    def next_search(self) -> None:
        if not self.search_results:
            self._notify("Nenhum resultado", "warning")
            return
        tree = self.tree1 if self.last_search_scope == "JSON 1" else self.tree2
        self.search_index = (self.search_index + 1) % len(self.search_results)
        self._highlight(tree, self.search_results[self.search_index])

    def clear_search(self) -> None:
        self.search_results = []
        self.search_index = 0
        self.last_search_scope = None

    def _toggle_elements_only(self) -> None:
        self.show_only_elements = self.elements_only_checkbox.isChecked()
        if self.logic.json1:
            self._build_tree(self.tree1, self.logic.json1)
        if self.logic.json2:
            self._build_tree(self.tree2, self.logic.json2)

    def _build_tree(self, tree: QtWidgets.QTreeWidget, data: object) -> None:
        tree.clear()
        root = QtWidgets.QTreeWidgetItem(["root"])
        root.setData(0, QtCore.Qt.ItemDataRole.UserRole, [])
        root.setForeground(0, QtGui.QBrush(QtGui.QColor("#5c5c5c")))
        tree.addTopLevelItem(root)
        if self.show_only_elements:
            self._insert_elements_only(tree, root, data, [])
        else:
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

    def _insert_elements_only(
        self,
        tree: QtWidgets.QTreeWidget,
        parent: QtWidgets.QTreeWidgetItem,
        value: object,
        path: List[int | str],
    ) -> None:
        if isinstance(value, dict):
            for key in ("children", "elements"):
                val = value.get(key)
                if isinstance(val, list):
                    for idx, element in enumerate(val):
                        if not isinstance(element, dict):
                            continue
                        label = element.get("id") or element.get("name") or f"[{idx}]"
                        item = QtWidgets.QTreeWidgetItem([label])
                        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, path + [key, idx])
                        item.setForeground(0, QtGui.QBrush(QtGui.QColor("#1b7fb3")))
                        font = item.font(0)
                        font.setBold(True)
                        item.setFont(0, font)
                        parent.addChild(item)
                        self._insert_elements_only(tree, item, element, path + [key, idx])
        elif isinstance(value, list):
            for idx, element in enumerate(value):
                self._insert_elements_only(tree, parent, element, path + [idx])

    def _highlight(self, tree: QtWidgets.QTreeWidget, item: QtWidgets.QTreeWidgetItem) -> None:
        ancestor = item.parent()
        while ancestor:
            tree.expandItem(ancestor)
            ancestor = ancestor.parent()
        tree.setCurrentItem(item)
        tree.scrollToItem(item)
        self._notify(f"Resultado {self.search_index + 1} de {len(self.search_results)}", "info")

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

    def colorize_hierarchy(self) -> None:
        try:
            self.logic.apply_name_colors()
            self._build_tree(self.tree2, self.logic.json2)
            self._notify("Cores aplicadas por hierarquia no config.json", "success")
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Falha ao colorir: {exc}", "error")

    def copy_animation(self) -> None:
        current = self.anim_list1.currentItem()
        if not current:
            self._notify("Selecione uma animação em Projeto 1", "warning")
            return
        path = current.data(QtCore.Qt.ItemDataRole.UserRole)
        try:
            self.logic.copy_animation_from_project1(path)
            self._notify("Animação copiada!", "success")
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Falha ao copiar animação: {exc}", "error")

    def paste_animation(self) -> None:
        if self.logic.animation_clipboard is None:
            self._notify("Nenhuma animação copiada", "warning")
            return
        if not self.logic.project2_archive:
            self._notify("Carregue o Projeto 2 primeiro", "warning")
            return
        mapping_dialog = AnimationMappingDialog(self, self.logic)
        if mapping_dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            mapping = mapping_dialog.get_mapping()
            try:
                self.logic.paste_animation_to_project2(mapping)
                self._notify("Animação colada no Projeto 2", "success")
                self._refresh_animation_lists()
            except Exception as exc:  # noqa: BLE001
                self._notify(f"Falha ao colar animação: {exc}", "error")

    def apply_frame_to_model(self) -> None:
        if not self.logic.project2_archive:
            self._notify("Carregue o Projeto 2 primeiro", "warning")
            return
        dialog = FrameApplyDialog(self, self.logic)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                project, path, frame_idx = dialog.selection()
                self.logic.apply_frame_to_model(project, path, frame_idx)
                self._build_tree(self.tree2, self.logic.json2)
                self._notify("Frame aplicado ao modelo", "success")
            except Exception as exc:  # noqa: BLE001
                self._notify(f"Falha ao aplicar frame: {exc}", "error")

    def _refresh_animation_lists(self) -> None:
        self.anim_list1.clear()
        self.anim_list2.clear()
        for item in self.logic.list_animations(1):
            list_item = QtWidgets.QListWidgetItem(item["label"])
            list_item.setData(QtCore.Qt.ItemDataRole.UserRole, item["path"])
            self.anim_list1.addItem(list_item)
        for item in self.logic.list_animations(2):
            list_item = QtWidgets.QListWidgetItem(item["label"])
            list_item.setData(QtCore.Qt.ItemDataRole.UserRole, item["path"])
            self.anim_list2.addItem(list_item)

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
            self._notify("Carrega o Projeto 2 ai antes, por favorzinho :)", "warning")
            return
        dialog = MovementDialog(self, self.logic)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._build_tree(self.tree2, self.logic.json2)
            if self.elements_only_checkbox.isChecked():
                self._toggle_elements_only()


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
            self._notify_parent("Nenhum elemento achado em JSON 2 :(", "warning")
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
        self._prefill_defaults(labels)

        self.debug_checkbox = QtWidgets.QCheckBox("DEBUG (salvar cada etapa)")
        layout.addWidget(self.debug_checkbox)

        self.skin_checkbox = QtWidgets.QCheckBox("skin x128")
        layout.addWidget(self.skin_checkbox)

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
                self._notify_parent(f"Escolhe algo para {key}, vai lá :)", "warning")
                return
            selection[key] = list(data)
        if len({tuple(path) for path in selection.values()}) != len(selection):
            self._notify_parent("Nao pode selecionar o mesmo elemento em duas opcoes nao :(", "warning")
            return
        try:
            debug_hook = self._build_debug_hook() if self.debug_checkbox.isChecked() else None
            skin_x128 = self.skin_checkbox.isChecked()
            self.logic.apply_movement_tool(selection, debug_hook=debug_hook, skin_x128=skin_x128)
            self._notify_parent("OBaaaaa - Deu bom :)", "success")
            self.accept()
        except Exception as exc:  # noqa: BLE001
            self._notify_parent(f"Deu esse erro aqui: {exc}", "error")

    def _build_debug_hook(self) -> Callable[[str], None]:
        parent_window = self.parent()
        step_labels = {
            "clone": "Depois de clonar os Anti_",
            "tamanho_posicao": "Depois de ajeitar tamanho/posicao",
            "hierarquia": "Depois de reorganizar hierarquia",
            "textura": "Depois de mexer na textura",
        }

        def _hook(step: str) -> None:
            label = step_labels.get(step, step)
            self._notify_parent(f"{label} - Chama o Salvar como... ai!", "info")
            if isinstance(parent_window, JSONMergerWindow):
                try:
                    parent_window.save_project2_as()
                except Exception as exc:  # noqa: BLE001
                    self._notify_parent(f"Salvar como falhou: {exc}", "warning")

        return _hook

    def _prefill_defaults(self, labels: list[tuple[str, str]]) -> None:
        name_targets = {
            "left_arm": "Left Arm",
            "right_arm": "Right Arm",
            "left_leg": "Left Leg",
            "right_leg": "Right Leg",
            "left_sleeve": "Left Sleeve",
            "right_sleeve": "Right Sleeve",
            "left_pants": "Left Pants Leg",
            "right_pants": "Right Pants Leg",
        }
        for key, _ in labels:
            target = name_targets.get(key, "").lower()
            combo = self.combos[key]
            for index in range(combo.count()):
                text = combo.itemText(index).lower()
                if text == target:
                    combo.setCurrentIndex(index)
                    break

    def _notify_parent(self, message: str, level: str = "info") -> None:
        parent = self.parent()
        if isinstance(parent, StatusMixin):
            parent._notify(message, level)
        elif parent and hasattr(parent, "_notify"):
            parent._notify(message, level)


class AnimationMappingDialog(QtWidgets.QDialog):
    def __init__(self, parent: JSONMergerWindow, logic: JSONMergerLogic) -> None:
        super().__init__(parent)
        self.logic = logic
        self.setWindowTitle("Mapear elementos da animação")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        if self.logic.animation_clipboard is None:
            if hasattr(self.parent(), "_notify"):
                self.parent()._notify("Nenhuma animação para mapear.", "error")
            self.reject()
            return
        source_ids = self.logic.extract_store_ids(self.logic.animation_clipboard)
        target_ids = self.logic.extract_store_ids_from_model()
        source_names = self.logic.storeid_name_map(project=1)
        target_names = self.logic.storeid_name_map(project=2)

        grid = QtWidgets.QGridLayout()
        self.combos: dict[int, QtWidgets.QComboBox] = {}
        rows_per_col = 8
        short = lambda val: str(val)[-6:] if isinstance(val, int) and len(str(val)) > 6 else str(val)
        for idx, sid in enumerate(source_ids):
            combo = QtWidgets.QComboBox()
            combo.setMinimumWidth(120)
            combo.setMaximumWidth(150)
            combo.view().setMinimumWidth(150)
            combo.addItem(f"Manter ({short(sid)})", userData=sid)
            for tid in target_ids:
                text = target_names.get(tid, str(tid))
                combo.addItem(f"{text} ({short(tid)})", userData=tid)
            row = idx % rows_per_col
            col = idx // rows_per_col
            label_text = source_names.get(sid, f"storeID {short(sid)}")
            label_widget = QtWidgets.QLabel(label_text)
            label_widget.setToolTip(str(sid))
            grid.addWidget(label_widget, row, col * 2)
            grid.addWidget(combo, row, col * 2 + 1)
            self.combos[sid] = combo
        layout.addLayout(grid)

        buttons = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        buttons.addWidget(btn_ok)

        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)

    def get_mapping(self) -> dict[int, int]:
        mapping: dict[int, int] = {}
        for sid, combo in self.combos.items():
            val = combo.currentData()
            if isinstance(val, int) and val != sid:
                mapping[sid] = val
        return mapping


class FrameApplyDialog(QtWidgets.QDialog):
    def __init__(self, parent: JSONMergerWindow, logic: JSONMergerLogic) -> None:
        super().__init__(parent)
        self.logic = logic
        self.setWindowTitle("Aplicar frame ao modelo")
        self.anim_entries: list[tuple[int, str, str]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.combo = QtWidgets.QComboBox()
        self._populate_animations()
        self.combo.currentIndexChanged.connect(self._on_anim_changed)
        layout.addWidget(self.combo)

        frame_row = QtWidgets.QHBoxLayout()
        frame_row.addWidget(QtWidgets.QLabel("Frame:"))
        self.spin = QtWidgets.QSpinBox()
        self.spin.setMinimum(0)
        frame_row.addWidget(self.spin)
        layout.addLayout(frame_row)

        buttons = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("Aplicar")
        btn_ok.clicked.connect(self.accept)
        buttons.addWidget(btn_ok)
        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)

        self._on_anim_changed(0)

    def _populate_animations(self) -> None:
        self.combo.clear()
        self.anim_entries.clear()
        for project in (1, 2):
            for item in self.logic.list_animations(project):
                label_prefix = "P1" if project == 1 else "P2"
                label = f"{label_prefix}: {item['label']}"
                self.combo.addItem(label, userData=(project, item["path"]))
                self.anim_entries.append((project, item["path"], label))

    def _on_anim_changed(self, index: int) -> None:
        data = self.combo.itemData(index)
        if not data:
            self.spin.setMaximum(0)
            return
        project, path = data
        try:
            anim = self.logic.load_animation(project, path)
            frames = anim.get("frames", [])
            total = len(frames) if isinstance(frames, list) else 0
            self.spin.setMaximum(max(total - 1, 0))
        except Exception:
            self.spin.setMaximum(0)

    def selection(self) -> tuple[int, str, int]:
        data = self.combo.currentData()
        if not data:
            raise ValueError("Nenhuma animação selecionada")
        project, path = data
        return project, path, self.spin.value()


def run_app() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = JSONMergerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
