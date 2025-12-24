import copy
import json
import re
import zipfile
from typing import Any, Callable, List, Optional


class JSONMergerLogic:
    def __init__(self) -> None:
        self.json1: Any = {}
        self.json2: Any = {}
        self.project2_path: str | None = None
        self.project2_archive: dict[str, bytes] = {}
        self.project1_archive: dict[str, bytes] = {}
        self.clipboard: Any = None
        self.clipboard_mode: str | None = None
        self.clipboard_orig_path: List[int | str] | None = None
        self.animation_clipboard: dict[str, Any] | None = None
        self.animation_clipboard_name: str | None = None
        self.animation_clipboard_project: int | None = None

    def load_project1(self, path: str) -> None:
        with zipfile.ZipFile(path, "r") as archive:
            self.project1_archive = {n: archive.read(n) for n in archive.namelist()}
            config_names = [n for n in archive.namelist() if n.lower().endswith("config.json")]
            if not config_names:
                raise ValueError("Nenhum config.json no projeto")
            raw_json = self._decode_bytes(self.project1_archive[config_names[0]])
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
        self.animation_clipboard = None
        self.animation_clipboard_name = None

    def apply_affixes(
        self,
        path: List[int | str],
        prefix: str,
        suffix: str,
        include_children: bool,
    ) -> None:
        node = self.get_by_path(self.json2, path)
        if not isinstance(node, dict):
            raise ValueError("Selecione um elemento válido para renomear")

        def rename_element(el: Any) -> None:
            if not isinstance(el, dict):
                return
            key = "name" if isinstance(el.get("name"), str) else ("id" if isinstance(el.get("id"), str) else None)
            if not key:
                return
            base = self._strip_numeric_suffix(str(el[key]))
            new_name = base
            if prefix:
                new_name = f"{prefix}{new_name}"
            if suffix:
                new_name = f"{new_name} {suffix}" if new_name else suffix
            el[key] = new_name.strip()

        rename_element(node)
        if include_children:
            for key in ("children", "elements"):
                child_list = node.get(key)
                if isinstance(child_list, list):
                    for child in child_list:
                        if isinstance(child, dict):
                            self._rename_descendants(child, prefix, suffix)

    def _rename_descendants(self, node: dict[str, Any], prefix: str, suffix: str) -> None:
        def rename(el: Any) -> None:
            if not isinstance(el, dict):
                return
            key = "name" if isinstance(el.get("name"), str) else ("id" if isinstance(el.get("id"), str) else None)
            if key:
                base = self._strip_numeric_suffix(str(el[key]))
                new_name = base
                if prefix:
                    new_name = f"{prefix}{new_name}"
                if suffix:
                    new_name = f"{new_name} {suffix}" if new_name else suffix
                el[key] = new_name.strip()
            for child_key in ("children", "elements"):
                arr = el.get(child_key)
                if isinstance(arr, list):
                    for ch in arr:
                        rename(ch)

        rename(node)

    @staticmethod
    def _strip_numeric_suffix(text: str) -> str:
        return re.sub(r"\s*\(\d+\)", "", text).strip()

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

    def compute_uv_bbox(self, element: dict[str, Any]) -> tuple[int, int, int, int] | None:
        if not isinstance(element, dict):
            return None
        if "faceUV" in element and isinstance(element["faceUV"], dict):
            coords = [
                face
                for face in element["faceUV"].values()
                if isinstance(face, dict) and {"sx", "sy", "ex", "ey"} <= face.keys()
            ]
            if coords:
                min_x = min(float(c["sx"]) for c in coords)
                max_x = max(float(c["ex"]) for c in coords)
                min_y = min(float(c["sy"]) for c in coords)
                max_y = max(float(c["ey"]) for c in coords)
                return int(min_x), int(min_y), int(max_x), int(max_y)

        uv = self._extract_uv(element)
        size = self._extract_size(element)
        if uv is None or size is None:
            return None
        u, v = uv
        x, y, z = size
        width = 2 * (x + z)
        height = y + z
        return int(u), int(v), int(u + width), int(v + height)

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
        skin_x128: bool = False,
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
            self._apply_per_face_uv(anti_refs[key]["obj"], skin_x128)
        self._call_debug(debug_hook, "textura")

    def list_animations(self, project: int) -> list[dict[str, str]]:
        archive = self.project1_archive if project == 1 else self.project2_archive
        items: list[dict[str, str]] = []
        for name in archive:
            if name.startswith("animations/") and name.lower().endswith(".json"):
                parsed = self._parse_animation_name(name.split("/")[-1])
                items.append(parsed | {"path": name})
        return items

    def copy_animation_from_project1(self, path: str) -> None:
        if path not in self.project1_archive:
            raise ValueError("Animação não encontrada no Projeto 1")
        raw = self._decode_bytes(self.project1_archive[path])
        self.animation_clipboard = json.loads(raw)
        self.animation_clipboard_name = path.split("/")[-1]
        self.animation_clipboard_project = 1

    def paste_animation_to_project2(self, mapping: dict[int, int]) -> None:
        if self.animation_clipboard is None or self.animation_clipboard_name is None:
            raise ValueError("Nenhuma animação copiada")
        cloned = copy.deepcopy(self.animation_clipboard)
        self._apply_storeid_mapping(cloned, mapping)
        target_path = f"animations/{self.animation_clipboard_name}"
        self.project2_archive[target_path] = json.dumps(cloned, indent=2, ensure_ascii=False).encode("utf-8")

    def load_animation(self, project: int, path: str) -> dict[str, Any]:
        archive = self.project1_archive if project == 1 else self.project2_archive
        if path not in archive:
            raise ValueError("Animação não encontrada")
        raw = self._decode_bytes(archive[path])
        return json.loads(raw)

    def move_frame(self, project: int, path: str, from_idx: int, to_idx: int) -> list[dict[str, Any]]:
        anim, frames = self._animation_with_frames(project, path)
        if from_idx < 0 or from_idx >= len(frames):
            raise ValueError("Índice de origem inválido")
        if to_idx < 0 or to_idx >= len(frames):
            raise ValueError("Índice de destino inválido")
        frame = frames.pop(from_idx)
        frames.insert(to_idx, frame)
        self._write_animation(project, path, anim)
        return frames

    def delete_frame(self, project: int, path: str, index: int) -> list[dict[str, Any]]:
        anim, frames = self._animation_with_frames(project, path)
        if index < 0 or index >= len(frames):
            raise ValueError("Índice inválido para excluir")
        frames.pop(index)
        self._write_animation(project, path, anim)
        return frames

    def duplicate_frame(self, project: int, path: str, index: int) -> list[dict[str, Any]]:
        anim, frames = self._animation_with_frames(project, path)
        if index < 0 or index >= len(frames):
            raise ValueError("Índice inválido para duplicar")
        frames.insert(index + 1, copy.deepcopy(frames[index]))
        self._write_animation(project, path, anim)
        return frames

    def insert_clean_frame(self, project: int, path: str, index: int) -> list[dict[str, Any]]:
        anim, frames = self._animation_with_frames(project, path)
        base_components = self._base_components_from_model(project)
        insert_at = min(max(index, 0), len(frames))
        frames.insert(insert_at, {"components": base_components})
        self._write_animation(project, path, anim)
        return frames

    def interpolate_frames(
        self, project: int, path: str, start_idx: int, end_idx: int, insert_count: int, new_name: str | None
    ) -> None:
        if insert_count <= 0:
            raise ValueError("Quantidade de frames deve ser positiva")
        anim = self.load_animation(project, path)
        frames = anim.get("frames")
        if not isinstance(frames, list):
            raise ValueError("Animação sem frames")
        if start_idx < 0 or end_idx >= len(frames) or start_idx >= end_idx:
            raise ValueError("Intervalo de frames inválido")

        start_frame = frames[start_idx]
        end_frame = frames[end_idx]
        start_map = self._components_by_storeid(start_frame)
        end_map = self._components_by_storeid(end_frame)
        union_ids = set(start_map) | set(end_map)

        new_frames: list[dict[str, Any]] = []
        for step in range(1, insert_count + 1):
            t = step / (insert_count + 1)
            comps: list[dict[str, Any]] = []
            for sid in union_ids:
                src = start_map.get(sid) or {}
                dst = end_map.get(sid) or {}
                if not isinstance(src, dict) or not isinstance(dst, dict):
                    continue
                comp = copy.deepcopy(src if src else dst)
                comp["storeID"] = sid
                comp["pos"] = self._lerp_vectors(src.get("pos"), dst.get("pos"), t)
                comp["rotation"] = self._lerp_vectors(src.get("rotation"), dst.get("rotation"), t)
                comps.append(comp)
            new_frames.append({"components": comps})

        frames_with_interp: list[dict[str, Any]] = []
        for idx, frame in enumerate(frames):
            frames_with_interp.append(frame)
            if idx == start_idx:
                frames_with_interp.extend(new_frames)

        anim["frames"] = frames_with_interp

        target_archive = self.project1_archive if project == 1 else self.project2_archive
        target_path = path
        if new_name:
            filename = new_name if new_name.lower().endswith(".json") else f"{new_name}.json"
            if not filename.startswith("animations/"):
                filename = f"animations/{filename}"
            target_path = filename
            anim["name"] = filename.split("/")[-1].replace(".json", "")
        target_archive[target_path] = json.dumps(anim, indent=2, ensure_ascii=False).encode("utf-8")

    def apply_frame_to_model(self, project: int, path: str, frame_index: int) -> None:
        if not self.project2_archive:
            raise ValueError("Carregue o Projeto 2 antes")
        anim = self.load_animation(project, path)
        frames = anim.get("frames", [])
        if not isinstance(frames, list) or frame_index < 0 or frame_index >= len(frames):
            raise ValueError("Frame inválido")
        frame = frames[frame_index]
        components = frame.get("components", []) if isinstance(frame, dict) else []
        if not isinstance(components, list):
            raise ValueError("Frame sem componentes")

        store_map = self._storeid_node_map(self.json2)
        base_transforms: dict[int, dict[str, Any]] = {}
        for comp in components:
            if not isinstance(comp, dict):
                continue
            sid = comp.get("storeID")
            if not isinstance(sid, int):
                continue
            base_transforms[sid] = {
                "pos": comp.get("pos"),
                "rotation": comp.get("rotation"),
            }
            if sid not in store_map:
                continue
            for target in store_map[sid]:
                self._apply_transform_to_node(target, comp)

        # Normaliza os frames subtraindo o frame aplicado
        if isinstance(frames, list):
            for frm in frames:
                comps = frm.get("components") if isinstance(frm, dict) else None
                if not isinstance(comps, list):
                    continue
                for comp in comps:
                    if not isinstance(comp, dict):
                        continue
                    sid = comp.get("storeID")
                    base = base_transforms.get(sid or -1)
                    if not base:
                        continue
                    if "pos" in base:
                        comp["pos"] = self._subtract_vectors(comp.get("pos"), base["pos"])
                    if "rotation" in base:
                        comp["rotation"] = self._subtract_vectors(
                            comp.get("rotation"), base["rotation"]
                        )

        target_archive = self.project1_archive if project == 1 else self.project2_archive
        target_archive[path] = json.dumps(anim, indent=2, ensure_ascii=False).encode("utf-8")

    def apply_name_colors(self) -> None:
        colors = [0x24FFFF, 0x00FF00, 0xFFFF00, 0x00FF89]

        def walk(node: Any, depth: int) -> None:
            if isinstance(node, dict):
                if any(k in node for k in ("name", "id", "storeID")):
                    node["nameColor"] = colors[depth % len(colors)]
                for key in ("children", "elements"):
                    val = node.get(key)
                    if isinstance(val, list):
                        for child in val:
                            walk(child, depth + 1)
            elif isinstance(node, list):
                for item in node:
                    walk(item, depth)

        walk(self.json2, 0)

    def extract_store_ids(self, animation_json: dict[str, Any]) -> list[int]:
        ids: set[int] = set()
        for frame in animation_json.get("frames", []):
            comps = frame.get("components", [])
            if isinstance(comps, list):
                for comp in comps:
                    store = comp.get("storeID")
                    if isinstance(store, int):
                        ids.add(store)
        return sorted(ids)

    def extract_store_ids_from_model(self) -> list[int]:
        ids: set[int] = set()

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                if "storeID" in node and isinstance(node["storeID"], int):
                    ids.add(node["storeID"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(self.json2)
        return sorted(ids)

    def storeid_name_map(self, project: int = 2) -> dict[int, str]:
        data = self.json2 if project == 2 else self.json1
        mapping: dict[int, str] = {}

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                sid = node.get("storeID")
                if isinstance(sid, int):
                    name = node.get("name") or node.get("id")
                    if isinstance(name, str) and sid not in mapping:
                        mapping[sid] = name
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(data)
        return mapping

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
        JSONMergerLogic._reorder_children_key(element)
        return children

    @staticmethod
    def _reorder_children_key(element: dict[str, Any]) -> None:
        if "children" not in element or not isinstance(element, dict):
            return
        children_value = element.pop("children")
        inserted = False
        # Tenta após DisableVanillaAnim
        if "DisableVanillaAnim" in element:
            new_data: dict[str, Any] = {}
            for key, value in element.items():
                new_data[key] = value
                if key == "DisableVanillaAnim":
                    new_data["children"] = children_value
                    inserted = True
            element.clear()
            element.update(new_data)
        # Se não inseriu, tenta antes de v
        if not inserted and "v" in element:
            new_data = {}
            for key, value in element.items():
                if key == "v":
                    new_data["children"] = children_value
                    inserted = True
                new_data[key] = value
            element.clear()
            element.update(new_data)
        # Caso nada se aplique, reinsere no final (comportamento anterior)
        if not inserted:
            element["children"] = children_value

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

    def _apply_per_face_uv(self, element: Any, skin_x128: bool = False) -> None:
        if not isinstance(element, dict):
            return
        tex_scale_raw = element.get("texScale", 1)
        tex_scale: float = tex_scale_raw if isinstance(tex_scale_raw, (int, float)) else 1
        base_uv = self._extract_uv(element)
        if "faceUV" in element and isinstance(element["faceUV"], dict):
            for face_name, coords in element["faceUV"].items():
                if not isinstance(coords, dict):
                    continue
                if face_name.lower() in {"up"}:
                    continue
                for key in ("sx", "ex", "sy", "ey"):
                    if key in coords and isinstance(coords[key], (int, float)):
                        coords[key] = coords[key] * (2 if skin_x128 else 1)
                        if key in ("sy", "ey"):
                            coords[key] += 6 * (2 if skin_x128 else 1)
                coords.setdefault("rot", "0")
                coords.setdefault("autoUV", True)
            if "down" in element["faceUV"]:
                coords = element["faceUV"]["down"]
                if isinstance(coords, dict):
                    coords.setdefault("rot", "0")
                    coords.setdefault("autoUV", True)
            if base_uv:
                element.setdefault("u", base_uv[0])
                element.setdefault("v", base_uv[1])
            return
        size = self._extract_size(element)
        if base_uv is None or size is None:
            return
        u, v = base_uv
        x, y, z = (component * tex_scale for component in size)
        u *= tex_scale
        v *= tex_scale
        scale = 2 if skin_x128 else 1
        x *= scale
        y *= scale
        z *= scale
        u *= scale
        v *= scale
        face_uv = {
            "east": {"sx": u, "sy": v + z, "ex": u + z, "ey": v + z + y},
            "south": {"sx": u + z + x, "sy": v + z, "ex": u + z + x + x, "ey": v + z + y},
            "north": {"sx": u + z, "sy": v + z, "ex": u + z + x, "ey": v + z + y},
            "west": {"sx": u + z + x + x, "sy": v + z, "ex": u + z + x + x + z, "ey": v + z + y},
            "down": {"sx": u + x + z, "sy": v, "ex": u + x + z + x, "ey": v + z},
        }
        for coords in face_uv.values():
            coords["sy"] += 6 * scale
            coords["ey"] += 6 * scale
            coords["rot"] = "0"
            coords["autoUV"] = True
        # Remove face down para mangas (sleeves) e calças (pants) originais
        name_val = element.get("name") or element.get("id") or ""
        if isinstance(name_val, str):
            lowered = name_val.lower()
            if ("sleeve" in lowered or "pants" in lowered) and "down" in face_uv:
                face_uv.pop("down", None)
        element["faceUV"] = face_uv
        element["u"] = u
        element["v"] = v

    def _parse_animation_name(self, filename: str) -> dict[str, str]:
        base = filename[:-5] if filename.lower().endswith(".json") else filename
        parts = base.split("_")
        prefix = parts[0] if parts else ""
        uuid = parts[-1] if parts else ""
        rest = parts[1:-1] if len(parts) > 2 else (parts[1:] if len(parts) == 2 else [])
        action = ""
        anim_name = ""
        if rest:
            anim_name = rest[-1]
            if len(rest) > 1:
                action = " ".join(rest[:-1]).replace("-", " ")
        label_type = "Pose" if prefix == "v" else "Value/Layer" if prefix == "g" else prefix
        return {
            "prefix": prefix,
            "type": label_type,
            "action": action,
            "name": anim_name,
            "uuid": uuid,
            "filename": filename,
            "label": f"{label_type}: {anim_name or '(sem nome)'}" + (f" ({action})" if action else ""),
        }

    def _apply_storeid_mapping(self, animation_json: dict[str, Any], mapping: dict[int, int]) -> None:
        for frame in animation_json.get("frames", []):
            comps = frame.get("components", [])
            if not isinstance(comps, list):
                continue
            for comp in comps:
                store = comp.get("storeID")
                if isinstance(store, int) and store in mapping:
                    comp["storeID"] = mapping[store]

    @staticmethod
    def _storeid_node_map(node: Any) -> dict[int, list[dict[str, Any]]]:
        result: dict[int, list[dict[str, Any]]] = {}

        def walk(cur: Any) -> None:
            if isinstance(cur, dict):
                sid = cur.get("storeID")
                if isinstance(sid, int):
                    result.setdefault(sid, []).append(cur)
                for value in cur.values():
                    walk(value)
            elif isinstance(cur, list):
                for item in cur:
                    walk(item)

        walk(node)
        return result

    @staticmethod
    def _components_by_storeid(frame: Any) -> dict[int, dict[str, Any]]:
        result: dict[int, dict[str, Any]] = {}
        comps = frame.get("components") if isinstance(frame, dict) else None
        if not isinstance(comps, list):
            return result
        for comp in comps:
            if isinstance(comp, dict):
                sid = comp.get("storeID")
                if isinstance(sid, int):
                    result[sid] = comp
        return result

    def _animation_with_frames(self, project: int, path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        anim = self.load_animation(project, path)
        frames = anim.get("frames")
        if not isinstance(frames, list):
            raise ValueError("Animação sem frames")
        return anim, frames

    def _write_animation(self, project: int, path: str, anim: dict[str, Any]) -> None:
        archive = self.project1_archive if project == 1 else self.project2_archive
        archive[path] = json.dumps(anim, indent=2, ensure_ascii=False).encode("utf-8")

    def _base_components_from_model(self, project: int) -> list[dict[str, Any]]:
        model = self.json1 if project == 1 else self.json2
        if not model:
            raise ValueError("Carregue o projeto correspondente antes")
        mapping = self._storeid_node_map(model)
        components: list[dict[str, Any]] = []
        for store_id in sorted(mapping):
            first = mapping[store_id][0]
            comp: dict[str, Any] = {"storeID": store_id}
            if "pos" in first:
                comp["pos"] = copy.deepcopy(first["pos"])
            if "rotation" in first:
                comp["rotation"] = copy.deepcopy(first["rotation"])
            components.append(comp)
        return components

    @staticmethod
    def _apply_transform_to_node(node: dict[str, Any], comp: dict[str, Any]) -> None:
        if not isinstance(node, dict):
            return
        if "pos" in comp and isinstance(comp["pos"], (dict, list)):
            node["pos"] = JSONMergerLogic._sum_vectors(node.get("pos"), comp["pos"])
        if "rotation" in comp and isinstance(comp["rotation"], (dict, list)):
            node["rotation"] = JSONMergerLogic._sum_vectors(
                node.get("rotation"), comp["rotation"]
            )

    @staticmethod
    def _sum_vectors(base: Any, delta: Any) -> Any:
        def _as_dict(vec: Any) -> dict[str, float] | None:
            if isinstance(vec, dict):
                return {
                    k: float(v)
                    for k, v in vec.items()
                    if k in {"x", "y", "z", "X", "Y", "Z"} and isinstance(v, (int, float))
                }
            if isinstance(vec, list) and len(vec) >= 3:
                return {"x": float(vec[0]), "y": float(vec[1]), "z": float(vec[2])}
            return None

        base_dict = _as_dict(base) or {"x": 0.0, "y": 0.0, "z": 0.0}
        delta_dict = _as_dict(delta) or {"x": 0.0, "y": 0.0, "z": 0.0}
        result = {
            "x": base_dict.get("x", 0.0) + delta_dict.get("x", 0.0),
            "y": base_dict.get("y", 0.0) + delta_dict.get("y", 0.0),
            "z": base_dict.get("z", 0.0) + delta_dict.get("z", 0.0),
        }
        return result

    @staticmethod
    def _subtract_vectors(base: Any, delta: Any) -> Any:
        def _as_dict(vec: Any) -> dict[str, float] | None:
            if isinstance(vec, dict):
                return {
                    k: float(v)
                    for k, v in vec.items()
                    if k in {"x", "y", "z", "X", "Y", "Z"} and isinstance(v, (int, float))
                }
            if isinstance(vec, list) and len(vec) >= 3:
                return {"x": float(vec[0]), "y": float(vec[1]), "z": float(vec[2])}
            return None

        base_dict = _as_dict(base) or {"x": 0.0, "y": 0.0, "z": 0.0}
        delta_dict = _as_dict(delta) or {"x": 0.0, "y": 0.0, "z": 0.0}
        result = {
            "x": base_dict.get("x", 0.0) - delta_dict.get("x", 0.0),
            "y": base_dict.get("y", 0.0) - delta_dict.get("y", 0.0),
            "z": base_dict.get("z", 0.0) - delta_dict.get("z", 0.0),
        }
        return result

    @staticmethod
    def _lerp_vectors(start: Any, end: Any, t: float) -> dict[str, float]:
        def _as_dict(vec: Any) -> dict[str, float]:
            if isinstance(vec, dict):
                return {
                    key.lower(): float(val)
                    for key, val in vec.items()
                    if key.lower() in {"x", "y", "z"} and isinstance(val, (int, float))
                }
            if isinstance(vec, list) and len(vec) >= 3:
                return {"x": float(vec[0]), "y": float(vec[1]), "z": float(vec[2])}
            return {"x": 0.0, "y": 0.0, "z": 0.0}

        s = _as_dict(start)
        e = _as_dict(end)
        return {
            "x": s.get("x", 0.0) + (e.get("x", 0.0) - s.get("x", 0.0)) * t,
            "y": s.get("y", 0.0) + (e.get("y", 0.0) - s.get("y", 0.0)) * t,
            "z": s.get("z", 0.0) + (e.get("z", 0.0) - s.get("z", 0.0)) * t,
        }

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
