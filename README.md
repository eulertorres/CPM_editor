<div align="right">
  <a href="./README.md"><button>English</button></a>
  <a href="./README_pt.md"><button>Português</button></a>
</div>

# CPM_Editor

CPM_Editor is a desktop helper for inspecting and manipulating **Custom Player Model (.cpmproject)** files. It lets you open two projects side-by-side (Projeto 1 and Projeto 2), copy or retarget model parts and animations, and automate repetitive authoring steps such as building the +Movment hierarchy or interpolating animation frames.

## Getting started
- **Requirements:** Python 3 with PyQt6 available.
- **Run:**
  ```bash
  python main.py
  ```
- **Projects:** Use the top-row buttons to load `Projeto 1` and `Projeto 2`. Project 2 is the editable target; `Salvar Projeto 2` overwrites the opened file and `Salvar como...` lets you pick a new destination (extension enforced to `.cpmproject`).
- **Options & theme:** Click **Opções** to toggle *Show only elements* (default on), *Dark mode* (global palette), and *Color elements from config.json* (applies stored `nameColor` to the tree). The top bar also shows a quick link to the GitHub repository.

## Key features
### Models tab
- **Element filtering & styling:** Elements vs. attributes are color-highlighted; an "apenas elementos" toggle trims the tree to roots and element nodes. Tree labels can display `nameColor` from the project (when enabled in Opções).
- **Status notifications:** Success/error/info messages appear in the fixed status bar with larger, legible font instead of pop-ups.
- **Copy/paste & search:** Quickly duplicate elements between projects and locate items via the search tool.
- **+Movment generator:**
  - Auto-detects standard limb names or lets you pick 8 parts manually.
  - Duplicates each limb with the `Anti_` prefix, builds the required arm/leg hierarchies, and keeps `children` ordered after `DisableVanillaAnim` and before `v`.
  - Normalizes sizes/positions (Y sizes 7 for primaries, 6 for Anti_ parts; Y position 6 for anti arms/legs), and preserves `u`/`v` even when applying face UVs.
  - Per-face UV handling shifts V by +6 (with scaling for `Tex scale 2` and the **skin x128** multiplier), keeps Down on Anti_ arms/legs, removes Down on pants, and offsets coordinates as requested.
  - **Debug checkbox** triggers "Salvar como..." after each internal step (clone, move, adjust size/position, apply UV).
- **Texture mover:** Visualizes `skin.png`, drawing the current UV rect and the displaced rect after `dU`/`dV` so you can preview offsets.
- **Hierarchy coloring tool:** Writes `nameColor` into Projeto 2 based on depth using the palette `24FFFF`, `00FF00`, `FFFF00`, `00FF89` (repeating by level) and rebuilds the tree accordingly.
- **Rename with prefix/suffix:** Choose an element, add prefix/suffix, strip any trailing "(N)" in names, and optionally cascade to all descendants.
- **Apply animation frame to model:** Select an animation and frame; frame transforms are **summed** into the current model pose, while the same offsets are subtracted from every frame of that animation to keep relative motion intact.

### Animations tab
- **Structured list:** Animations are read from the `animations/` folder inside the `.cpmproject`, with names parsed from filenames (Pose files start with `v_`, Value/Layer files with `g_`).
- **Copy & paste between projects:** Copy animations from Projeto 1 into a clipboard, then paste into Projeto 2. StoreIDs remain the authoritative mapping, but the UI shows element names and short IDs; mapping combos wrap into columns to stay compact.
- **Frame interpolation:** Insert user-defined in-between frames between two reference frames, interpolating position and rotation for every involved component. Save back into the same animation or into a new file.
- **Apply frame to model:** (Shared workflow from Models tab) enables retargeting poses directly into the model structure.

## Dark mode
Enable in **Opções** to apply a consistent dark palette (dark backgrounds, light text, highlighted selections) across all widgets.

## Change log
### alpha-0.1.0 (main)
+ Open two `.cpmproject` files, browse/edit `config.json` trees, and save changes into Projeto 2.
+ Copy/paste model elements and adjust UV/positions through the existing tools and search dialog.

### beta-0.2.0 (this branch)
+ Added "Salvar como..." with default paths, enforced extension, and debug hooks.
+ Added visual distinction between elements and attributes in the tree and an element-only view (default on).
+ Added the +Movment generator: auto-picks limbs, clones with `Anti_`, builds arm/leg hierarchies, reorders `children`, resizes/repositions parts, and preserves `u`/`v` while applying per-face UV offsets (including Down handling rules and the **skin x128** scaler).
+ Added per-step debug saving inside +Movment and ensured UV shifts account for Tex scale and V offsets.
+ Added status-bar messaging to replace pop-ups.
+ Added dark mode toggle affecting the entire UI and reorganized the element-only toggle into the Opções dialog.
+ Added optional rendering of tree item colors based on `nameColor` from `config.json` and a hierarchy-coloring tool using the new palette.
+ Added toolbar label "-by Sushi_nucelar" with GitHub quick link.
+ Added texture mover preview that overlays current and displaced UV regions on `skin.png`.
+ Added prefix/suffix renaming tool that strips numeric suffixes and can recurse through children.
+ Added animations tab to load animation JSONs from the `animations/` folder, parse names from filenames, and list Projeto 1/2 separately.
+ Added copy/paste of animations between projects using StoreID mapping, with UI showing element names, compact dropdowns, and column-wrapped mapping controls.
+ Added frame application tool that sums animation frame transforms into the model and subtracts offsets from all frames of the source animation.
+ Added frame interpolation tool to generate intermediate frames with blended position/rotation and save into the same or a new animation.
+ Added "skin x128" UV scaling option and refined Down-face handling (kept for Anti_ arms/legs, removed for pants).

