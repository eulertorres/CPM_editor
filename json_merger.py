import copy
import json
import zipfile
from typing import Any, Callable, List, Optional


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

    def save_project2_as(self, path: str) -> None:
        if not self.project2_archive:
            raise ValueError("Carregue o Projeto 2 antes de salvar")
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in self.project2_archive.items():
                if name.lower().endswith("config.json"):
                    archive.writestr(name, json.dumps(self.json2, indent=2, ensure_ascii=False))
                else:
                    archive.writestr(name, data)
        self.project2_path = path

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

    def list_elements(self) -> list[tuple[str, List[int | str]]]:
        results: list[tuple[str, List[int | str]]] = []

        def walk(node: Any, path: List[int | str]) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in {"elements", "children"} and isinstance(value, list):
                        for idx, element in enumerate(value):
                            if isinstance(element, dict):
                                label = element.get("id") or element.get("name") or f"{key}[{idx}]"
                                results.append((str(label), path + [key, idx]))
                                walk(element, path + [key, idx])
                    else:
                        walk(value, path + [key])
            elif isinstance(node, list):
                for idx, item in enumerate(node):
                    walk(item, path + [idx])

        walk(self.json2, [])
        return results

    def apply_movement_tool(
        self,
        selection: dict[str, List[int | str]],
        debug_hook: Optional[Callable[[str], None]] = None,
    ) -> None:
        if not self.project2_archive:
            raise ValueError("Naao tem que carregar o project 2 antes :d")
        required_keys = {
            "left_arm",
            "right_arm",
            "left_leg",
            "right_leg",
            "left_sleeve",
            "right_sleeve",
            "left_pants",
            "right_pants",
        }
        if set(selection) != required_keys:
            raise ValueError("Faltou selecionar alguma coisa ai")
        refs = {key: self._element_ref(path) for key, path in selection.items()}
        anti_refs: dict[str, dict[str, Any]] = {}
        for key, ref in refs.items():
            clone = copy.deepcopy(ref["obj"])
            self._prefix_element_name(clone, "Anti_")
            ref["parent_list"].append(clone)
            anti_refs[key] = {"obj": clone, "parent_list": ref["parent_list"]}
        self._call_debug(debug_hook, "clone")
        for key in required_keys:
            self._set_y_size(refs[key]["obj"], 7)
        for anti in anti_refs.values():
            self._set_y_size(anti["obj"], 6)
        for key in ("left_arm", "right_arm", "left_leg", "right_leg"):
            self._set_y_position(anti_refs[key]["obj"], 6)
        self._call_debug(debug_hook, "tamanho_posicao")
        self._build_hierarchy(
            parent_ref=refs["left_arm"],
            child_refs=[
                anti_refs["left_arm"],
                refs["left_sleeve"],
            ],
            anti_child_ref=anti_refs["left_sleeve"],
        )
        self._build_hierarchy(
            parent_ref=refs["right_arm"],
            child_refs=[
                anti_refs["right_arm"],
                refs["right_sleeve"],
            ],
            anti_child_ref=anti_refs["right_sleeve"],
        )
        self._build_hierarchy(
            parent_ref=refs["left_leg"],
            child_refs=[
                anti_refs["left_leg"],
                refs["left_pants"],
            ],
            anti_child_ref=anti_refs["left_pants"],
        )
        self._build_hierarchy(
            parent_ref=refs["right_leg"],
            child_refs=[
                anti_refs["right_leg"],
                refs["right_pants"],
            ],
            anti_child_ref=anti_refs["right_pants"],
        )
        self._call_debug(debug_hook, "hierarquia")
        for key in (
            "left_arm",
            "right_arm",
            "left_leg",
            "right_leg",
            "left_sleeve",
            "right_sleeve",
            "left_pants",
            "right_pants",
        ):
            self._apply_per_face_uv(anti_refs[key]["obj"])
        self._call_debug(debug_hook, "textura")

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

    def _element_ref(self, path: List[int | str]) -> dict[str, Any]:
        parent = self.get_by_path(self.json2, path[:-1])
        if not isinstance(parent, list):
            raise ValueError("Elemento selecionado não está dentro de uma lista")
        return {
            "obj": self.get_by_path(self.json2, path),
            "parent_list": parent,
        }

    @staticmethod
    def _prefix_element_name(element: Any, prefix: str) -> None:
        if not isinstance(element, dict):
            return
        if "name" in element and isinstance(element["name"], str):
            element["name"] = f"{prefix}{element['name']}"
        elif "id" in element and isinstance(element["id"], str):
            element["id"] = f"{prefix}{element['id']}"

    @staticmethod
    def _ensure_children(element: dict[str, Any]) -> list:
        children = element.get("children")
        if not isinstance(children, list):
            children = []
            element["children"] = children
        return children

    def _build_hierarchy(
        self,
        parent_ref: dict[str, Any],
        child_refs: list[dict[str, Any]],
        anti_child_ref: dict[str, Any],
    ) -> None:
        parent_obj = parent_ref["obj"]
        parent_children = self._ensure_children(parent_obj)
        for child in child_refs:
            self._move_to_children(parent_children, child)
        anti_parent_children = self._ensure_children(child_refs[0]["obj"])
        self._move_to_children(anti_parent_children, anti_child_ref)

    def _move_to_children(self, target_children: list, child_ref: dict[str, Any]) -> None:
        child_obj = child_ref["obj"]
        parent_list = child_ref["parent_list"]
        try:
            if parent_list is not target_children and child_obj in parent_list:
                parent_list.remove(child_obj)
        except ValueError:
            pass
        if child_obj not in target_children:
            target_children.append(child_obj)
        child_ref["parent_list"] = target_children

    @staticmethod
    def _set_y_size(element: Any, value: int | float) -> None:
        if not isinstance(element, dict):
            return
        size = element.get("size")
        if isinstance(size, list) and len(size) >= 2:
            size[1] = value
        elif isinstance(size, dict):
            for key in ("y", "Y", "height"):
                if key in size:
                    size[key] = value

    @staticmethod
    def _set_y_position(element: Any, value: int | float) -> None:
        if not isinstance(element, dict):
            return
        for key in ("pos", "position", "origin", "translate", "pivot"):
            pos = element.get(key)
            if isinstance(pos, list) and len(pos) >= 2:
                pos[1] = value
            elif isinstance(pos, dict):
                for axis_key in ("y", "Y"):
                    if axis_key in pos:
                        pos[axis_key] = value

    def _apply_per_face_uv(self, element: Any) -> None:
        if not isinstance(element, dict):
            return
        tex_scale_raw = element.get("texScale", 1)
        tex_scale: float = tex_scale_raw if isinstance(tex_scale_raw, (int, float)) else 1
        if "faceUV" in element and isinstance(element["faceUV"], dict):
            for face_name, coords in element["faceUV"].items():
                if not isinstance(coords, dict):
                    continue
                if face_name.lower() in {"up", "down"}:
                    continue
                for key in ("sy", "ey"):
                    if key in coords and isinstance(coords[key], (int, float)):
                        coords[key] += 6
            return
        base_uv = self._extract_uv(element)
        size = self._extract_size(element)
        if base_uv is None or size is None:
            return
        u, v = base_uv
        x, y, z = (component * tex_scale for component in size)
        u *= tex_scale
        v *= tex_scale
        face_uv = {
            "north": {"sx": u + z, "sy": v + z, "ex": u + z + x, "ey": v + z + y},
            "east": {"sx": u, "sy": v + z, "ex": u + z, "ey": v + z + y},
            "south": {"sx": u + z + x, "sy": v + z, "ex": u + z + x + x, "ey": v + z + y},
            "west": {"sx": u + z + x + x, "sy": v + z, "ex": u + z + x + x + z, "ey": v + z + y},
            "up": {"sx": u + z, "sy": v, "ex": u + z + x, "ey": v + z},
            "down": {"sx": u + x + z, "sy": v, "ex": u + x + z + x, "ey": v + z},
        }
        for name, coords in face_uv.items():
            if name in {"up", "down"}:
                continue
            coords["sy"] += 6
            coords["ey"] += 6
        element["faceUV"] = face_uv
        element.pop("uv", None)
        element.pop("u", None)
        element.pop("v", None)

    @staticmethod
    def _extract_uv(element: dict[str, Any]) -> tuple[float, float] | None:
        if "uv" in element:
            uv = element["uv"]
            if isinstance(uv, list) and len(uv) >= 2:
                return float(uv[0]), float(uv[1])
        if "u" in element and "v" in element:
            u = element["u"]
            v = element["v"]
            if isinstance(u, (int, float)) and isinstance(v, (int, float)):
                return float(u), float(v)
        return None

    @staticmethod
    def _extract_size(element: dict[str, Any]) -> tuple[float, float, float] | None:
        size = element.get("size")
        if isinstance(size, list) and len(size) >= 3:
            return float(size[0]), float(size[1]), float(size[2])
        if isinstance(size, dict):
            x = size.get("x") if "x" in size else size.get("X")
            y = size.get("y") if "y" in size else size.get("Y")
            z = size.get("z") if "z" in size else size.get("Z")
            if isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(z, (int, float)):
                return float(x), float(y), float(z)
        return None

    @staticmethod
    def _call_debug(debug_hook: Optional[Callable[[str], None]], step: str) -> None:
        if debug_hook is None:
            return
        try:
            debug_hook(step)
        except Exception:
            pass
