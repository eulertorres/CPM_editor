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
            target.statusBar().setStyleSheet(
                f"QStatusBar{{color:{color}; padding:4px; font-size:12px;}}"
            )
            target.statusBar().showMessage(message, 6000)
        else:
            QtWidgets.QMessageBox.information(self, "Info", message)


class OptionsDialog(QtWidgets.QDialog):
    def __init__(
        self, parent: QtWidgets.QWidget, elements_only: bool, dark_mode: bool, show_colors: bool
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Opções")
        self.elements_only = elements_only
        self.dark_mode = dark_mode
        self.show_colors = show_colors
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.chk_elements = QtWidgets.QCheckBox("Mostrar apenas elementos")
        self.chk_elements.setChecked(self.elements_only)
        layout.addWidget(self.chk_elements)

        self.chk_dark = QtWidgets.QCheckBox("Modo escuro")
        self.chk_dark.setChecked(self.dark_mode)
        layout.addWidget(self.chk_dark)

        self.chk_colors = QtWidgets.QCheckBox("Colorir elementos pelo config.json")
        self.chk_colors.setChecked(self.show_colors)
        layout.addWidget(self.chk_colors)

        buttons = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QtWidgets.QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def values(self) -> dict[str, bool]:
        return {
            "elements_only": self.chk_elements.isChecked(),
            "dark_mode": self.chk_dark.isChecked(),
            "show_colors": self.chk_colors.isChecked(),
        }


class JSONMergerWindow(QtWidgets.QMainWindow, StatusMixin):
    def __init__(self) -> None:
        super().__init__()
        self.logic = JSONMergerLogic()
        self.search_results: list[QtWidgets.QTreeWidgetItem] = []
        self.search_index = 0
        self.last_search_scope: str | None = None
        self.show_only_elements = True
        self.dark_mode_enabled = False
        self.show_element_colors = False
        self.current_animation: tuple[int, str, str] | None = None
        self._setup_ui()
        self.statusBar().showMessage("Pronto")

    def _setup_ui(self) -> None:
        self.setWindowTitle("CPM_Editor")
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

        self.btn_options = QtWidgets.QPushButton("Opções")
        self.btn_options.clicked.connect(self.open_options_dialog)
        top_button_row.addWidget(self.btn_options)

        self.by_label = QtWidgets.QLabel("-by Sushi_nucelar")
        self.by_label.setStyleSheet("font-size:9px; color:#888;")
        top_button_row.addWidget(self.by_label)

        self.btn_github = QtWidgets.QPushButton()
        self.btn_github.setFixedSize(24, 24)
        self.btn_github.setIcon(QtGui.QIcon("assets/git.png"))
        self.btn_github.setIconSize(QtCore.QSize(18, 18))
        self.btn_github.setToolTip("Abrir repositório")
        self.btn_github.clicked.connect(self.open_repo)
        top_button_row.addWidget(self.btn_github)

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
        tools_row.addWidget(
            self._create_tool_button("🔤", "Prefixo/Sufixo em nomes", self.open_affix_dialog)
        )

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

        self.btn_interp_frames = QtWidgets.QPushButton("Interpolar frames")
        self.btn_interp_frames.clicked.connect(self.interpolate_animation_frames)
        anim_buttons.addWidget(self.btn_interp_frames)

        anim_layout.addLayout(anim_buttons)

        anim_splitter = QtWidgets.QSplitter()
        anim_layout.addWidget(anim_splitter, 1)

        anim_left = QtWidgets.QWidget()
        anim_left_layout = QtWidgets.QVBoxLayout(anim_left)
        anim_left_layout.addWidget(QtWidgets.QLabel("Animações Projeto 1"))
        self.anim_list1 = QtWidgets.QListWidget()
        self.anim_list1.currentItemChanged.connect(
            lambda cur, prev: self._on_animation_selected(1, cur)
        )
        anim_left_layout.addWidget(self.anim_list1)
        anim_splitter.addWidget(anim_left)

        anim_right = QtWidgets.QWidget()
        anim_right_layout = QtWidgets.QVBoxLayout(anim_right)
        anim_right_layout.addWidget(QtWidgets.QLabel("Animações Projeto 2"))
        self.anim_list2 = QtWidgets.QListWidget()
        self.anim_list2.currentItemChanged.connect(
            lambda cur, prev: self._on_animation_selected(2, cur)
        )
        anim_right_layout.addWidget(self.anim_list2)
        anim_splitter.addWidget(anim_right)

        anim_splitter.setStretchFactor(0, 1)
        anim_splitter.setStretchFactor(1, 1)

        timeline_box = QtWidgets.QGroupBox("Timeline")
        timeline_layout = QtWidgets.QVBoxLayout(timeline_box)
        self.timeline_header = QtWidgets.QLabel("Nenhuma animação selecionada")
        timeline_layout.addWidget(self.timeline_header)

        controls = QtWidgets.QHBoxLayout()
        self.btn_move_left = QtWidgets.QPushButton("Mover ←")
        self.btn_move_left.clicked.connect(lambda: self._move_frame(-1))
        controls.addWidget(self.btn_move_left)

        self.btn_move_right = QtWidgets.QPushButton("Mover →")
        self.btn_move_right.clicked.connect(lambda: self._move_frame(1))
        controls.addWidget(self.btn_move_right)

        self.btn_add_clean = QtWidgets.QPushButton("Adicionar frame limpo")
        self.btn_add_clean.clicked.connect(self._add_clean_frame)
        controls.addWidget(self.btn_add_clean)

        self.btn_duplicate = QtWidgets.QPushButton("Duplicar frame")
        self.btn_duplicate.clicked.connect(self._duplicate_frame)
        controls.addWidget(self.btn_duplicate)

        self.btn_delete = QtWidgets.QPushButton("Excluir frame")
        self.btn_delete.clicked.connect(self._delete_frame)
        controls.addWidget(self.btn_delete)

        controls.addStretch(1)
        timeline_layout.addLayout(controls)

        self.timeline_list = QtWidgets.QListWidget()
        self.timeline_list.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.timeline_list.setWrapping(True)
        self.timeline_list.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.timeline_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.timeline_list.currentItemChanged.connect(self._update_frame_details)
        timeline_layout.addWidget(self.timeline_list)

        details_box = QtWidgets.QGroupBox("Elementos modificados no frame")
        details_layout = QtWidgets.QVBoxLayout(details_box)
        self.frame_elements_label = QtWidgets.QLabel("Selecione um frame para ver os elementos")
        details_layout.addWidget(self.frame_elements_label)
        self.frame_elements_list = QtWidgets.QListWidget()
        self.frame_elements_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        details_layout.addWidget(self.frame_elements_list)

        copy_row = QtWidgets.QHBoxLayout()
        self.btn_copy_transform = QtWidgets.QPushButton(
            "Copiar pos/rot + filhos para outro frame"
        )
        self.btn_copy_transform.clicked.connect(self._copy_element_transform)
        copy_row.addWidget(self.btn_copy_transform)
        copy_row.addStretch(1)
        details_layout.addLayout(copy_row)

        timeline_layout.addWidget(details_box)

        anim_layout.addWidget(timeline_box)

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

    def _toggle_elements_only(self, state: bool) -> None:
        self.show_only_elements = state
        if self.logic.json1:
            self._build_tree(self.tree1, self.logic.json1)
        if self.logic.json2:
            self._build_tree(self.tree2, self.logic.json2)

    def _toggle_dark_mode(self, enabled: bool) -> None:
        self.dark_mode_enabled = enabled
        app = QtWidgets.QApplication.instance()
        if not app:
            return
        if enabled:
            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(40, 40, 40))
            palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(235, 235, 235))
            palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(28, 28, 28))
            palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(45, 45, 45))
            palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(60, 60, 60))
            palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor(235, 235, 235))
            palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(235, 235, 235))
            palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(50, 50, 50))
            palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(235, 235, 235))
            palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor(255, 85, 85))
            palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(90, 130, 255))
            palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(15, 15, 15))
            palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(100, 160, 255))
            app.setPalette(palette)
            app.setStyleSheet(
                """
                QWidget { color: #e5e5e5; background-color: #282828; }
                QTreeWidget, QListWidget, QTableWidget, QTextEdit, QLineEdit, QComboBox, QSpinBox {
                    background-color: #1f1f1f; color: #e5e5e5; selection-background-color: #5a82ff; }
                QPushButton { background-color: #3a3a3a; color: #e5e5e5; border: 1px solid #4a4a4a; padding: 4px 6px; }
                QPushButton:hover { background-color: #4a4a4a; }
                QMenu { background-color: #2f2f2f; color: #e5e5e5; }
                QStatusBar { background-color: #202020; color: #e5e5e5; }
                QToolTip { color: #e5e5e5; background-color: #3a3a3a; border: 1px solid #5a5a5a; }
                """
            )
        else:
            app.setPalette(app.style().standardPalette())
            app.setStyleSheet("")

    def open_options_dialog(self) -> None:
        dialog = OptionsDialog(
            self, self.show_only_elements, self.dark_mode_enabled, self.show_element_colors
        )
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            opts = dialog.values()
            if opts["dark_mode"] != self.dark_mode_enabled:
                self._toggle_dark_mode(opts["dark_mode"])
            if opts["elements_only"] != self.show_only_elements:
                self._toggle_elements_only(opts["elements_only"])
            if opts["show_colors"] != self.show_element_colors:
                self.show_element_colors = opts["show_colors"]
                self._build_tree(self.tree1, self.logic.json1)
                self._build_tree(self.tree2, self.logic.json2)

    def open_repo(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/eulertorres/CPM_editor"))

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

    def _color_from_namecolor(self, element: dict[str, object]) -> QtGui.QColor:
        value = element.get("nameColor") if isinstance(element, dict) else None
        color_val: int | None = None
        if isinstance(value, int):
            color_val = value
        elif isinstance(value, str):
            try:
                color_val = int(value)
            except ValueError:
                color_val = None
        if color_val is not None:
            return QtGui.QColor(f"#{color_val:06x}")
        return QtGui.QColor("#1b7fb3")

    def _label_color(self, element: dict[str, object]) -> QtGui.QColor:
        if self.show_element_colors:
            return self._color_from_namecolor(element)
        return QtGui.QColor("#7a7a7a")

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
                color = self._label_color(val) if isinstance(val, dict) else QtGui.QColor("#7a7a7a")
                item.setForeground(0, QtGui.QBrush(color))
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
                    item.setForeground(0, QtGui.QBrush(self._label_color(element)))
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
                        item.setForeground(0, QtGui.QBrush(self._label_color(element)))
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

    def interpolate_animation_frames(self) -> None:
        if not (self.logic.project1_archive or self.logic.project2_archive):
            self._notify("Carregue algum projeto antes", "warning")
            return
        dialog = FrameInterpolationDialog(self, self.logic)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                selection = dialog.selection()
                self.logic.interpolate_frames(**selection)
                self._refresh_animation_lists()
                self._notify("Frames interpolados com sucesso", "success")
            except Exception as exc:  # noqa: BLE001
                self._notify(f"Falha ao interpolar frames: {exc}", "error")

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

        self._clear_timeline()

    def _clear_timeline(self) -> None:
        self.timeline_list.clear()
        self.timeline_header.setText("Nenhuma animação selecionada")
        self.current_animation = None
        self._clear_frame_elements()

    def _on_animation_selected(
        self, project: int, item: QtWidgets.QListWidgetItem | None
    ) -> None:
        if item is None:
            self._clear_timeline()
            return
        other_list = self.anim_list2 if project == 1 else self.anim_list1
        other_list.blockSignals(True)
        other_list.clearSelection()
        other_list.blockSignals(False)
        path = item.data(QtCore.Qt.ItemDataRole.UserRole)
        label = item.text()
        if not isinstance(path, str):
            self._clear_timeline()
            return
        self.current_animation = (project, path, label)
        self._load_timeline()

    def _load_timeline(self) -> None:
        self.timeline_list.clear()
        if not self.current_animation:
            self.timeline_header.setText("Nenhuma animação selecionada")
            return
        project, path, label = self.current_animation
        try:
            anim = self.logic.load_animation(project, path)
            frames = anim.get("frames", [])
            if not isinstance(frames, list):
                raise ValueError("Animação sem frames")
            for idx, frame in enumerate(frames):
                components = frame.get("components", []) if isinstance(frame, dict) else []
                comp_count = len(components) if isinstance(components, list) else 0
                item = QtWidgets.QListWidgetItem(f"Frame {idx}\n{comp_count} comps")
                item.setData(QtCore.Qt.ItemDataRole.UserRole, idx)
                self.timeline_list.addItem(item)
            self.timeline_header.setText(
                f"{label} — {len(frames)} frame(s) (Projeto {project})"
            )
            if self.timeline_list.count() > 0:
                self.timeline_list.setCurrentRow(0)
            else:
                self._clear_frame_elements()
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Falha ao carregar timeline: {exc}", "error")
            self._clear_timeline()
        self._update_frame_details()

    def _current_frame_index(self) -> int | None:
        row = self.timeline_list.currentRow()
        if row < 0:
            return None
        return row

    def _clear_frame_elements(self) -> None:
        self.frame_elements_list.clear()
        self.frame_elements_label.setText("Selecione um frame para ver os elementos")

    def _update_frame_details(
        self, current: QtWidgets.QListWidgetItem | None = None, previous: QtWidgets.QListWidgetItem | None = None
    ) -> None:
        del previous
        if current is None or not self.current_animation:
            self._clear_frame_elements()
            return
        project, path, _ = self.current_animation
        try:
            index = self._current_frame_index()
            if index is None:
                self._clear_frame_elements()
                return
            elements = self.logic.frame_component_hierarchy(project, path, index)
            self.frame_elements_list.clear()
            modified_count = 0
            for element in elements:
                label = ("    " * element.get("depth", 0)) + element.get("name", "")
                item = QtWidgets.QListWidgetItem(label)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, element.get("storeID"))
                if element.get("modified"):
                    item.setForeground(QtGui.QBrush(QtGui.QColor("#006400")))
                    modified_count += 1
                self.frame_elements_list.addItem(item)
            count = len(elements)
            self.frame_elements_label.setText(
                f"{modified_count} elemento(s) modificados de {count} no frame {index}"
            )
        except Exception as exc:  # noqa: BLE001
            self._notify(str(exc), "error")
            self._clear_frame_elements()

    def _copy_element_transform(self) -> None:
        try:
            project, path, _ = self._require_animation()
            src_frame = self._current_frame_index()
            if src_frame is None:
                raise ValueError("Selecione um frame de origem na timeline")
            selected_element = self.frame_elements_list.currentItem()
            if selected_element is None:
                raise ValueError("Selecione um elemento na lista do frame")
            store_id = selected_element.data(QtCore.Qt.ItemDataRole.UserRole)
            if not isinstance(store_id, int):
                raise ValueError("Elemento sem storeID válido")
            max_frame = self.timeline_list.count() - 1
            target_frame, ok = QtWidgets.QInputDialog.getInt(
                self,
                "Copiar para frame",
                "Número do frame de destino (0-index)",
                value=src_frame,
                min=0,
                max=max_frame if max_frame >= 0 else 0,
            )
            if not ok:
                return
            self.logic.copy_element_transform(project, path, src_frame, target_frame, store_id)
            self._notify("Transformações copiadas para o frame de destino", "success")
            self.timeline_list.setCurrentRow(target_frame)
        except Exception as exc:  # noqa: BLE001
            self._notify(str(exc), "error")

    def _require_animation(self) -> tuple[int, str, str]:
        if not self.current_animation:
            raise ValueError("Selecione uma animação primeiro")
        return self.current_animation

    def _move_frame(self, delta: int) -> None:
        try:
            project, path, _ = self._require_animation()
            index = self._current_frame_index()
            if index is None:
                raise ValueError("Selecione um frame para mover")
            target = index + delta
            if target < 0 or target >= self.timeline_list.count():
                raise ValueError("Não é possível mover além dos limites")
            self.logic.move_frame(project, path, index, target)
            self._load_timeline()
            self.timeline_list.setCurrentRow(target)
            self._notify("Frame movido", "success")
        except Exception as exc:  # noqa: BLE001
            self._notify(str(exc), "error")

    def _delete_frame(self) -> None:
        try:
            project, path, _ = self._require_animation()
            index = self._current_frame_index()
            if index is None:
                raise ValueError("Selecione um frame para excluir")
            self.logic.delete_frame(project, path, index)
            self._load_timeline()
            new_index = min(index, self.timeline_list.count() - 1)
            if new_index >= 0:
                self.timeline_list.setCurrentRow(new_index)
            self._notify("Frame excluído", "success")
        except Exception as exc:  # noqa: BLE001
            self._notify(str(exc), "error")

    def _duplicate_frame(self) -> None:
        try:
            project, path, _ = self._require_animation()
            index = self._current_frame_index()
            if index is None:
                raise ValueError("Selecione um frame para duplicar")
            self.logic.duplicate_frame(project, path, index)
            self._load_timeline()
            self.timeline_list.setCurrentRow(index + 1)
            self._notify("Frame duplicado", "success")
        except Exception as exc:  # noqa: BLE001
            self._notify(str(exc), "error")

    def _add_clean_frame(self) -> None:
        try:
            project, path, _ = self._require_animation()
            index = self._current_frame_index()
            insert_at = (index + 1) if index is not None else 0
            self.logic.insert_clean_frame(project, path, insert_at)
            self._load_timeline()
            self.timeline_list.setCurrentRow(insert_at)
            self._notify("Frame limpo inserido", "success")
        except Exception as exc:  # noqa: BLE001
            self._notify(str(exc), "error")

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
            if self.show_only_elements:
                self._toggle_elements_only(True)

    def open_affix_dialog(self) -> None:
        if not self.logic.json2:
            self._notify("Carregue o Projeto 2 primeiro", "warning")
            return
        dialog = NameAffixDialog(self, self.logic)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                path, prefix, suffix, include_children = dialog.values()
                self.logic.apply_affixes(path, prefix, suffix, include_children)
                self._build_tree(self.tree2, self.logic.json2)
                self._notify("Prefixo/Sufixo aplicados", "success")
            except Exception as exc:  # noqa: BLE001
                self._notify(f"Falha ao aplicar prefixo/sufixo: {exc}", "error")


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


class NameAffixDialog(QtWidgets.QDialog):
    def __init__(self, parent: JSONMergerWindow, logic: JSONMergerLogic) -> None:
        super().__init__(parent)
        self.logic = logic
        self.setWindowTitle("Prefixo/Sufixo")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        self.element_combo = QtWidgets.QComboBox()
        for label, path in self.logic.list_elements():
            self.element_combo.addItem(label, userData=path)
        form.addRow("Elemento", self.element_combo)

        self.prefix_input = QtWidgets.QLineEdit()
        form.addRow("Prefixo", self.prefix_input)
        self.suffix_input = QtWidgets.QLineEdit()
        form.addRow("Sufixo", self.suffix_input)

        self.children_checkbox = QtWidgets.QCheckBox("Aplicar nos filhos")
        form.addRow("", self.children_checkbox)

        layout.addLayout(form)

        buttons = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("Aplicar")
        btn_ok.clicked.connect(self.accept)
        buttons.addWidget(btn_ok)

        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)

        layout.addLayout(buttons)

    def values(self) -> tuple[list[int | str], str, str, bool]:
        path = self.element_combo.currentData()
        if path is None:
            raise ValueError("Selecione um elemento")
        return (
            list(path),
            self.prefix_input.text().strip(),
            self.suffix_input.text().strip(),
            self.children_checkbox.isChecked(),
        )


class UVShiftDialog(QtWidgets.QDialog):
    def __init__(self, parent: JSONMergerWindow) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Mover textura (Shift UV)")
        current = self.parent_window.tree2.currentItem()
        if not current:
            self.parent_window._notify("Selecione elemento em JSON 2 para ajustar UV", "warning")
            self.reject()
            return
        self.element_path = self.parent_window._item_path(current)
        self.element = self.parent_window.logic.get_by_path(self.parent_window.logic.json2, self.element_path)
        self.texture_pixmap = self._load_texture_pixmap()
        self.current_bbox = self.parent_window.logic.compute_uv_bbox(self.element)
        self.scene: QtWidgets.QGraphicsScene | None = None
        self.current_rect: QtWidgets.QGraphicsRectItem | None = None
        self.shift_rect: QtWidgets.QGraphicsRectItem | None = None
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

        if self.texture_pixmap and self.current_bbox:
            self.scene = QtWidgets.QGraphicsScene(self)
            self.scene.addPixmap(self.texture_pixmap)
            self.view = QtWidgets.QGraphicsView(self.scene)
            self.view.setRenderHints(
                QtGui.QPainter.RenderHint.Antialiasing
                | QtGui.QPainter.RenderHint.SmoothPixmapTransform
            )
            layout.addWidget(self.view)
            self._draw_bboxes()
            self.du_input.valueChanged.connect(self._draw_bboxes)
            self.dv_input.valueChanged.connect(self._draw_bboxes)
        else:
            layout.addWidget(QtWidgets.QLabel("Sem prévia de textura disponível."))

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

    def _load_texture_pixmap(self) -> QtGui.QPixmap | None:
        if not self.parent_window.logic.project2_archive:
            return None
        for name, data in self.parent_window.logic.project2_archive.items():
            if name.lower().endswith("skin.png"):
                pixmap = QtGui.QPixmap()
                if pixmap.loadFromData(data):
                    return pixmap
        return None

    def _draw_bboxes(self) -> None:
        if not self.scene or not self.current_bbox:
            return
        du = int(self.du_input.value())
        dv = int(self.dv_input.value())
        x1, y1, x2, y2 = self.current_bbox
        shifted = (x1 + du, y1 + dv, x2 + du, y2 + dv)
        for item in (self.current_rect, self.shift_rect):
            if item:
                self.scene.removeItem(item)
        pen_current = QtGui.QPen(QtGui.QColor("red"))
        pen_current.setWidth(2)
        pen_shift = QtGui.QPen(QtGui.QColor("green"))
        pen_shift.setWidth(2)
        self.current_rect = self.scene.addRect(QtCore.QRectF(x1, y1, x2 - x1, y2 - y1), pen_current)
        self.shift_rect = self.scene.addRect(
            QtCore.QRectF(shifted[0], shifted[1], shifted[2] - shifted[0], shifted[3] - shifted[1]),
            pen_shift,
        )
        self.view.fitInView(self.scene.itemsBoundingRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)


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


class FrameInterpolationDialog(QtWidgets.QDialog):
    def __init__(self, parent: JSONMergerWindow, logic: JSONMergerLogic) -> None:
        super().__init__(parent)
        self.logic = logic
        self.anim_entries: list[tuple[int, str, str]] = []
        self.setWindowTitle("Interpolar frames")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        self.combo_anim = QtWidgets.QComboBox()
        self._populate_animations()
        self.combo_anim.currentIndexChanged.connect(self._on_anim_changed)
        layout.addWidget(self.combo_anim)

        form = QtWidgets.QFormLayout()
        self.spin_start = QtWidgets.QSpinBox()
        self.spin_start.setMinimum(0)
        form.addRow("Frame inicial", self.spin_start)

        self.spin_end = QtWidgets.QSpinBox()
        self.spin_end.setMinimum(0)
        form.addRow("Frame final", self.spin_end)

        self.spin_insert = QtWidgets.QSpinBox()
        self.spin_insert.setMinimum(1)
        self.spin_insert.setValue(1)
        form.addRow("Frames a inserir", self.spin_insert)
        layout.addLayout(form)

        self.radio_same = QtWidgets.QRadioButton("Salvar na mesma animação")
        self.radio_new = QtWidgets.QRadioButton("Salvar como nova")
        self.radio_same.setChecked(True)
        radios = QtWidgets.QHBoxLayout()
        radios.addWidget(self.radio_same)
        radios.addWidget(self.radio_new)
        layout.addLayout(radios)

        self.new_name_edit = QtWidgets.QLineEdit()
        self.new_name_edit.setPlaceholderText("Novo nome do arquivo (opcional)")
        self.new_name_edit.setEnabled(False)
        layout.addWidget(self.new_name_edit)

        self.radio_new.toggled.connect(self._toggle_new_name)

        buttons = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("Interpolar")
        ok_btn.clicked.connect(self._validate_and_accept)
        cancel_btn = QtWidgets.QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self._on_anim_changed(0)

    def _populate_animations(self) -> None:
        self.combo_anim.clear()
        self.anim_entries.clear()
        for project in (1, 2):
            for item in self.logic.list_animations(project):
                label_prefix = "P1" if project == 1 else "P2"
                label = f"{label_prefix}: {item['label']}"
                self.combo_anim.addItem(label, userData=(project, item["path"]))
                self.anim_entries.append((project, item["path"], label))

    def _toggle_new_name(self, enabled: bool) -> None:
        self.new_name_edit.setEnabled(enabled)

    def _on_anim_changed(self, index: int) -> None:
        data = self.combo_anim.itemData(index)
        if not data:
            self.spin_start.setMaximum(0)
            self.spin_end.setMaximum(0)
            return
        project, path = data
        try:
            anim = self.logic.load_animation(project, path)
            frames = anim.get("frames", [])
            total = len(frames) if isinstance(frames, list) else 0
            max_idx = max(total - 1, 0)
            self.spin_start.setMaximum(max_idx)
            self.spin_end.setMaximum(max_idx)
            self.spin_end.setValue(min(1, max_idx))
            base_name = path.split("/")[-1]
            self.new_name_edit.setText(base_name.replace(".json", "_interp.json"))
        except Exception:
            self.spin_start.setMaximum(0)
            self.spin_end.setMaximum(0)

    def _validate_and_accept(self) -> None:
        if self.spin_start.value() >= self.spin_end.value():
            QtWidgets.QMessageBox.warning(self, "Aviso", "Frame inicial deve ser menor que o final")
            return
        if self.radio_new.isChecked() and not self.new_name_edit.text().strip():
            QtWidgets.QMessageBox.warning(self, "Aviso", "Informe o novo nome do arquivo")
            return
        self.accept()

    def selection(self) -> dict[str, object]:
        data = self.combo_anim.currentData()
        if not data:
            raise ValueError("Nenhuma animação selecionada")
        project, path = data
        new_name = self.new_name_edit.text().strip() if self.radio_new.isChecked() else None
        return {
            "project": project,
            "path": path,
            "start_idx": self.spin_start.value(),
            "end_idx": self.spin_end.value(),
            "insert_count": self.spin_insert.value(),
            "new_name": new_name,
        }


def run_app() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = JSONMergerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
