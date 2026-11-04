---
name: vm-asset-openings
description: Make a new ASSET SET of doors or windows for the VM engine (VM_Doors, VM_Windows, VM_DoorHandles) from a glTF/OBJ pack or a procedural model, through pack_ingest.py, so houses can get other door and window styles (barn doors, sash windows, boarded-up windows, shop fronts...). Use when the user wants different doors or windows, sends a pack or link, or a window/door looks wrong (floating, ajar, mis-scaled, glass missing).
---

# Door and window asset sets

Shared rules and the build/test loop are in `../vm-new-building-part/WORKFLOW.md`.

**Status (v2.29): mature.** The fit, slot and world-space checks have passed since v2.6,
cut openings and jambs since v2.15, glass since v2.18. Scale probe: see
`../vm-new-building-part/SCALE_STATUS.md`.

## How the engine uses a set
- `VM_SceneDetailer_Door` puts **one** front door on a ground-floor wall
  (Column Select First Only, Max Instances 1, Sill Height 0, nominal opening
  1.4 × 2.1).
- `VM_SceneDetailer_Windows` fills every slot:
  - Sill Height 0.9, nominal opening 0.8 × 0.9, Scale 0.5;
  - one row per 3 m storey;
  - it is the **last** opening layer, so it cuts the holes, jambs and glass for
    the door and the windows.

  Both layers use Opening Fit "Scale To Face": every variant is scaled into the
  slot, down to Min Fit Scale 0.5.
- `AUTO_COLLECTIONS`: Primary Props → `VM_Doors` / `VM_Windows`.
- The cut hole, the jamb depth (Wall Depth 0.15, Opening Inset 0.03) and the glass
  pane are all derived from the **instance bounds**, so the bbox must be the
  opening.
  - Glass needs `vm_openmark` on the opening, and Cut Openings + Window Glass on.
    Broken panes break by `vm_gbrk`.
  - The door hole runs `DOOR_SILL_CUT` 0.1 m below the threshold.

## The asset contract (WALLFLAT slab, what `pack_ingest.py` produces)
- One mesh object, transforms applied, named `Door_NN` / `Window_NN` /
  `DoorHandle_NN`.
- **Frame:** thin axis is Y (depth), height is Z, width is X. The origin is centred
  in X, at **y = 0 on the back (wall-contact) face**, and at the **base** in Z
  (Stand On Face Base / the sill contract). Proper rotation only, no mirroring.
- **Flat:** depth ≤ 25 % of min(width, height). The panel is closed, not ajar.
  `pack_ingest` quarantines a part if its PCA thickness is over 1.05 × the bbox
  depth, or if it is several disjoint shells.
- Real-world metres. Packs in cm are auto-scaled by 0.01. Over 4 m is flagged.
- The bbox **is** the opening: frame and casing included, nothing sticking out
  (handles go in `VM_DoorHandles` as PROP).

## Making a new set
1. **Reference:** ask the user for an image of the door or window style. Agree the
   size and the storey it is for.
2. **Get the pack:**
   - Poly Haven or another CC0 source; Sketchfab links go to the user to download.
   - Put it in its own new, empty directory under
     `~/Documents/ViperMeshAssets/props/doors|windows/<Pack>/`, with `SOURCE.txt`.
   - Open it with `-I` Python only.
3. **Ingest dry-run:**
   `pack_ingest.ingest_pack(path, out_dir=ROOT, parent=col)` → `<Pack>_ingest.json`.
   Read the classes and the quarantine reasons. Fix a mis-classified part in the
   *source* (or add a generic rule to `pack_ingest.py`). **Never** add
   pack-specific parameters: the adapter stays zero-config. Its own docstring is
   the rule book.
4. **Wire:** add the pack path to `PACK_PATHS` and, in `ingest_packs`, the
   `pack_objs("<Pack>", "WALLFLAT")` list for doors or windows.
   - For an alternative style rather than more variety, make sibling collections
     `VM_Doors_<Style>` / `VM_Windows_<Style>` and a library preset that selects
     them (see the `vm-asset-cladding` step 5).
   - Add the new `<Pack>_ingest.json` to the repo, like the others.
5. **Check:** the build's fit and slot checks; containment (`containment_check`);
   the door back plane = planks thickness + tolerance and front proud ≥ 5 mm
   (`accept(a)`); the window sill at 0.9 m world even with an unapplied object
   scale (`world-space:`); glass in every cut window.
6. **Look:** a close-up from outside and one from inside the jamb.
   - The siding must stop at the casing with no gap.
   - No floating door ("ajar" packs are the usual cause).

## Lessons (append; newest last)
- A swung-open door inside its own bbox fit "flush" but hung off the wall.
  That is why the PCA-thickness quarantine exists.
- Doors climbing onto roofs (tower + wing shapes): Ground Floor Only, Max Base
  Height 0.5 and the per-face anchoring (`bugfix(roof-door)` check).
- Windows are taken by any "tall opening" test unless it also checks for a
  bottom near the ground (the v2.29 yard).
