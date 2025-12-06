import copy
import json
import zipfile
from typing import Any, List


class JSONMergerLogic:
    def __init__(self) -> None:
        self.json1: Any = {}
        self.json2: Any = {}
        self.project2_path: str | None = None
        self.project2_archive: dict[str, bytes] = {}
        self.clipboard: Any = None
        self.clipboard_mode: str | None = None
        self.clipboard_orig_path: List[int | str] | None = None

    def load_project1(self, path: str) -> None:
        raw_json = self._read_config_from_archive(path)
        self.json1 = json.loads(raw_json)

    def load_project2(self, path: str) -> None:
        with zipfile.ZipFile(path, "r") as archive:
            names = [n for n in archive.namelist() if n.lower().endswith("config.json")]
            if not names:
                raise ValueError("Nenhum config.json no projeto")
            self.project2_archive = {n: archive.read(n) for n in archive.namelist()}
            self.project2_path = path
            raw_json = self._decode_bytes(self.project2_archive[names[0]])
            self.json2 = json.loads(raw_json)

    def save_project2(self) -> None:
        if not self.project2_path:
            raise ValueError("Carregue o Projeto 2 antes de salvar")
        with zipfile.ZipFile(self.project2_path, "w") as archive:
            for name, data in self.project2_archive.items():
                if name.lower().endswith("config.json"):
                    archive.writestr(name, json.dumps(self.json2, indent=2, ensure_ascii=False))
                else:
                    archive.writestr(name, data)

    def clear_clipboard(self) -> None:
        self.clipboard = None
        self.clipboard_mode = None
        self.clipboard_orig_path = None

    def get_by_path(self, data: Any, path: List[int | str]) -> Any:
        current = data
        for part in path:
            current = current[part]
        return current

    def remove_by_path(self, data: Any, path: List[int | str]) -> None:
        parent = self.get_by_path(data, path[:-1])
        idx = path[-1]
        if isinstance(parent, list):
            parent.pop(idx)
        else:
            raise ValueError("Não é lista para remover")

    def adjust_uv(self, node: Any, du: int, dv: int) -> None:
        if isinstance(node, dict):
            if node.get("texture") and "u" in node and "v" in node:
                node["u"] += du
                node["v"] += dv
            if "faceUV" in node and isinstance(node["faceUV"], dict):
                for face in node["faceUV"].values():
                    if isinstance(face, dict):
                        if "ex" in face:
                            face["ex"] += du
                        if "sx" in face:
                            face["sx"] += du
                        if "ey" in face:
                            face["ey"] += dv
                        if "sy" in face:
                            face["sy"] += dv
            for val in node.values():
                self.adjust_uv(val, du, dv)
        elif isinstance(node, list):
            for item in node:
                self.adjust_uv(item, du, dv)

    def copy_from_json1(self, path: List[int | str]) -> None:
        self.clipboard = copy.deepcopy(self.get_by_path(self.json1, path))
        self.clipboard_mode = "copy"

    def move_from_json2(self, path: List[int | str]) -> None:
        self.clipboard = copy.deepcopy(self.get_by_path(self.json2, path))
        self.clipboard_mode = "move"
        self.clipboard_orig_path = path

    def paste_to_json2(self, dest_path: List[int | str]) -> None:
        if self.clipboard is None:
            raise ValueError("Clipboard vazio")
        parent = self.get_by_path(self.json2, dest_path)
        if isinstance(parent, list):
            parent.append(self.clipboard)
        elif isinstance(parent, dict):
            if isinstance(parent.get("elements"), list):
                parent["elements"].append(self.clipboard)
            elif isinstance(parent.get("children"), list):
                parent["children"].append(self.clipboard)
            else:
                raise ValueError("Destino não suporta inserir lista")
        else:
            raise ValueError("Destino não é lista nem dict")
        if self.clipboard_mode == "move" and self.clipboard_orig_path is not None:
            try:
                self.remove_by_path(self.json2, self.clipboard_orig_path)
            except Exception:
                pass
        self.clear_clipboard()

    def _read_config_from_archive(self, path: str) -> str:
        with zipfile.ZipFile(path, "r") as archive:
            names = [n for n in archive.namelist() if n.lower().endswith("config.json")]
            if not names:
                raise ValueError("Nenhum config.json no projeto")
            raw = archive.read(names[0])
            return self._decode_bytes(raw)

    @staticmethod
    def _decode_bytes(raw: bytes) -> str:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")
