import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import json
import copy
import os
import zipfile

class JSONMergerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CPM Project JSON Merger")
        self.geometry("900x650")
        ctk.set_appearance_mode("System")

        # Dados dos JSONs e mapeamento de caminhos para cada item na árvore
        self.json1 = {}
        self.json2 = {}
        self.path_map1 = {}
        self.path_map2 = {}

        # Para manipular o projeto .cpmproject 2
        self.project2_path = None
        self.project2_archive = {}

        # Clipboard para copiar/mover elementos
        self.clipboard = None
        self.clipboard_mode = None  # "copy" ou "move"
        self.clipboard_orig_path = None

        # Variáveis para busca
        self.search_var = ctk.StringVar()
        self.search_scope = ctk.StringVar(value="JSON 1")
        self.search_results = []
        self.search_index = 0

        # Variáveis para deslocamento UV
        self.du_var = ctk.StringVar(value="0")
        self.dv_var = ctk.StringVar(value="0")

        self._create_widgets()

    def _create_widgets(self):
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)

        # Carregar projetos
        ctk.CTkButton(btn_frame, text="Carregar Projeto 1", command=self.load_project1).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Carregar Projeto 2", command=self.load_project2).pack(side="left", padx=5)

        # Busca
        ctk.CTkEntry(btn_frame, width=200, placeholder_text="Buscar...", textvariable=self.search_var).pack(side="left", padx=10)
        ctk.CTkOptionMenu(btn_frame, values=["JSON 1", "JSON 2"], variable=self.search_scope).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Buscar", command=self.search).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Próximo", command=self.next_search).pack(side="left", padx=5)

        # Copiar / Mover / Colar
        ctk.CTkButton(btn_frame, text="Copiar", command=self.copy_element).pack(side="left", padx=20)
        ctk.CTkButton(btn_frame, text="Mover", command=self.move_element).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Colar", command=self.paste_element).pack(side="left", padx=5)

        # Shift UV
        ctk.CTkLabel(btn_frame, text="dU:").pack(side="left", padx=(20,2))
        ctk.CTkEntry(btn_frame, width=60, textvariable=self.du_var).pack(side="left", padx=2)
        ctk.CTkLabel(btn_frame, text="dV:").pack(side="left", padx=(10,2))
        ctk.CTkEntry(btn_frame, width=60, textvariable=self.dv_var).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Shift UV", command=self.shift_uv).pack(side="left", padx=10)

        # Salvar de volta no .cpmproject
        ctk.CTkButton(btn_frame, text="Salvar Projeto 2", command=self.save_project2).pack(side="left", padx=20)

        # Área das árvores
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))

        # Árvore JSON1
        left = ctk.CTkFrame(main_frame)
        left.pack(side="left", fill="both", expand=True, padx=(0,5))
        ctk.CTkLabel(left, text="JSON 1").pack(anchor="w")
        self.tree1 = ttk.Treeview(left)
        self.tree1.pack(fill="both", expand=True, side="left")
        ttk.Scrollbar(left, orient="vertical", command=self.tree1.yview).pack(fill="y", side="right")
        self.tree1.configure(yscrollcommand=self.tree1.yview)

        # Árvore JSON2
        right = ctk.CTkFrame(main_frame)
        right.pack(side="left", fill="both", expand=True, padx=(5,0))
        ctk.CTkLabel(right, text="JSON 2").pack(anchor="w")
        self.tree2 = ttk.Treeview(right)
        self.tree2.pack(fill="both", expand=True, side="left")
        ttk.Scrollbar(right, orient="vertical", command=self.tree2.yview).pack(fill="y", side="right")
        self.tree2.configure(yscrollcommand=self.tree2.yview)

    def load_project1(self):
        path = filedialog.askopenfilename(
            filetypes=[("CPM Project","*.cpmproject")], title="Selecione o .cpmproject"
        )
        if not path: return
        try:
            with zipfile.ZipFile(path, 'r') as z:
                names = [n for n in z.namelist() if n.lower().endswith('config.json')]
                if not names:
                    raise ValueError("Nenhum config.json no projeto")
                raw = z.read(names[0])
                # tenta UTF-8, senão Latin-1
                try:
                    text = raw.decode('utf-8')
                except UnicodeDecodeError:
                    text = raw.decode('latin-1')
                self.json1 = json.loads(text)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar Projeto 1:\n{e}")
            return
        self._build_tree(self.tree1, self.json1, self.path_map1)
        self.clear_search()
        self.clear_clipboard()

    def load_project2(self):
        path = filedialog.askopenfilename(
            filetypes=[("CPM Project","*.cpmproject")], title="Selecione o .cpmproject"
        )
        if not path: return
        try:
            with zipfile.ZipFile(path, 'r') as z:
                names = [n for n in z.namelist() if n.lower().endswith('config.json')]
                if not names:
                    raise ValueError("Nenhum config.json no projeto")
                # carrega todo o archive em memória
                self.project2_archive = {n: z.read(n) for n in z.namelist()}
                self.project2_path = path
                raw = self.project2_archive[names[0]]
                try:
                    text = raw.decode('utf-8')
                except UnicodeDecodeError:
                    text = raw.decode('latin-1')
                self.json2 = json.loads(text)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar Projeto 2:\n{e}")
            return
        self._build_tree(self.tree2, self.json2, self.path_map2)
        self.clear_search()
        self.clear_clipboard()


    def save_project2(self):
        if not self.project2_path:
            messagebox.showwarning("Aviso", "Carregue o Projeto 2 antes de salvar")
            return
        try:
            with zipfile.ZipFile(self.project2_path, 'w') as z:
                for name, data in self.project2_archive.items():
                    if name.lower().endswith('config.json'):
                        # substitui pelo JSON modificado
                        z.writestr(name, json.dumps(self.json2, indent=2, ensure_ascii=False))
                    else:
                        z.writestr(name, data)
            messagebox.showinfo("Sucesso", "Projeto 2 atualizado com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar Projeto 2:\n{e}")

    def _build_tree(self, tree, data, path_map):
        for iid in tree.get_children():
            tree.delete(iid)
        path_map.clear()
        root = tree.insert("", "end", text="root", open=True)
        path_map[root] = []
        self._insert_items(tree, root, data, path_map, [])

    def _insert_items(self, tree, parent, value, path_map, path):
        if isinstance(value, dict):
            for k, v in value.items():
                iid = tree.insert(parent, "end", text=str(k), open=False)
                path_map[iid] = path + [k]
                self._insert_items(tree, iid, v, path_map, path + [k])
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    label = item.get("id") or item.get("name") or f"[{idx}]"
                else:
                    label = f"[{idx}]"
                iid = tree.insert(parent, "end", text=label, open=False)
                path_map[iid] = path + [idx]
                self._insert_items(tree, iid, item, path_map, path + [idx])
        else:
            iid = tree.insert(parent, "end", text=repr(value), open=False)
            path_map[iid] = path

    def _get_by_path(self, data, path):
        for p in path:
            data = data[p]
        return data

    def _remove_by_path(self, data, path):
        parent = self._get_by_path(data, path[:-1])
        idx = path[-1]
        if isinstance(parent, list):
            parent.pop(idx)
        else:
            raise ValueError("Não é lista para remover")

    def copy_element(self):
        sel = self.tree1.focus()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione algo em JSON 1")
            return
        path = self.path_map1[sel]
        self.clipboard = copy.deepcopy(self._get_by_path(self.json1, path))
        self.clipboard_mode = "copy"
        messagebox.showinfo("Clipboard", "Elemento copiado")

    def move_element(self):
        sel = self.tree2.focus()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione algo em JSON 2 para mover")
            return
        path = self.path_map2[sel]
        self.clipboard = copy.deepcopy(self._get_by_path(self.json2, path))
        self.clipboard_mode = "move"
        self.clipboard_orig_path = path
        messagebox.showinfo("Clipboard", "Elemento marcado para mover. Agora selecione destino e clique Colar")

    def paste_element(self):
        if not self.clipboard:
            messagebox.showwarning("Aviso", "Clipboard vazio")
            return
        sel = self.tree2.focus()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione destino em JSON 2")
            return
        dest_path = self.path_map2[sel]
        parent = self._get_by_path(self.json2, dest_path)
        if isinstance(parent, list):
            parent.append(self.clipboard)
        elif isinstance(parent, dict):
            if isinstance(parent.get("elements"), list):
                parent["elements"].append(self.clipboard)
            elif isinstance(parent.get("children"), list):
                parent["children"].append(self.clipboard)
            else:
                messagebox.showerror("Erro", "Destino não suporta inserir lista")
                return
        else:
            messagebox.showerror("Erro", "Destino não é lista nem dict")
            return
        if self.clipboard_mode == "move":
            try:
                self._remove_by_path(self.json2, self.clipboard_orig_path)
            except:
                pass
        self._build_tree(self.tree2, self.json2, self.path_map2)
        self.clear_clipboard()
        messagebox.showinfo("Sucesso", "Elemento colado")

    def shift_uv(self):
        try:
            du = int(self.du_var.get())
            dv = int(self.dv_var.get())
        except ValueError:
            messagebox.showerror("Erro", "dU e dV devem ser inteiros")
            return
        sel = self.tree2.focus()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione elemento em JSON 2 para ajustar UV")
            return
        element = self._get_by_path(self.json2, self.path_map2[sel])
        self._adjust_uv(element, du, dv)
        self._build_tree(self.tree2, self.json2, self.path_map2)
        messagebox.showinfo("Sucesso", f"UV ajustado em dU={du}, dV={dv}")

    def _adjust_uv(self, node, du, dv):
        if isinstance(node, dict):
            if node.get("texture") and "u" in node and "v" in node:
                node["u"] += du
                node["v"] += dv
            if "faceUV" in node and isinstance(node["faceUV"], dict):
                for face in node["faceUV"].values():
                    if isinstance(face, dict):
                        if "ex" in face: face["ex"] += du
                        if "sx" in face: face["sx"] += du
                        if "ey" in face: face["ey"] += dv
                        if "sy" in face: face["sy"] += dv
            for val in node.values():
                self._adjust_uv(val, du, dv)
        elif isinstance(node, list):
            for item in node:
                self._adjust_uv(item, du, dv)

    def clear_clipboard(self):
        self.clipboard = None
        self.clipboard_mode = None
        self.clipboard_orig_path = None

    def clear_search(self):
        self.search_results = []
        self.search_index = 0

    def search(self):
        q = self.search_var.get().strip().lower()
        if not q:
            messagebox.showwarning("Aviso", "Digite algo para buscar")
            return
        tree = self.tree1 if self.search_scope.get() == "JSON 1" else self.tree2
        def walk(parent):
            for c in tree.get_children(parent):
                yield c
                yield from walk(c)
        self.search_results = [iid for iid in walk("") if q in str(tree.item(iid, "text")).lower()]
        if not self.search_results:
            messagebox.showinfo("Busca", "Nada encontrado")
            return
        self.search_index = 0
        self._highlight(tree, self.search_results[0])

    def next_search(self):
        if not self.search_results:
            messagebox.showwarning("Aviso", "Nenhum resultado")
            return
        tree = self.tree1 if self.search_scope.get() == "JSON 1" else self.tree2
        self.search_index = (self.search_index + 1) % len(self.search_results)
        self._highlight(tree, self.search_results[self.search_index])

    def _highlight(self, tree, iid):
        p = tree.parent(iid)
        while p:
            tree.item(p, open=True)
            p = tree.parent(p)
        tree.selection_set(iid)
        tree.see(iid)
        tree.focus(iid)
        messagebox.showinfo("Busca", f"Resultado {self.search_index+1} de {len(self.search_results)}")

if __name__ == "__main__":
    app = JSONMergerApp()
    app.mainloop()
