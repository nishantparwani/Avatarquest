"""
train_body_model.py
-------------------
Master script for Part 1.  Runs the full pipeline:
    1. Parse the input GLB mesh
    2. Train the body-part MLP on CAPE data (if not already trained)
    3. Segment the mesh into body regions
    4. Extract skeleton joints
    5. Save outputs: avatar.png, joints.json, segmentation.npz

Usage:
    python train_body_model.py

Or pass a custom GLB path:
    python train_body_model.py C:/path/to/model.glb

Install everything at once:
    pip install trimesh numpy torch pillow scipy pygltflib

Expected folder structure for CAPE data:
    cape_data/
    └── 00096/
        ├── 00096_shortshort_hips_000.npz
        ├── 00096_shortshort_hips_001.npz
        └── ... (any .npz files)
"""

import os
import sys
import json
import numpy as np

# ── CONFIGURE PATHS HERE ──────────────────────────────────────────────────────
# Adjust these to match your actual file locations on Windows
GLB_INPUT_PATH = r"C:/Users/nisha/Downloads/files (2) (1)/4_15_2026.glb"
CAPE_DATA_DIR  = r"C:/Users/nisha/Downloads/files (2) (1)/cape_data/00096"
MODEL_SAVE_DIR = r"C:/Users/nisha/Downloads/files (2) (1)/models"
OUTPUT_DIR     = r"C:/Users/nisha/Downloads/files (2) (1)/outputs"
# ─────────────────────────────────────────────────────────────────────────────

MODEL_SAVE_PATH = os.path.join(MODEL_SAVE_DIR, "body_classifier.pt")
AVATAR_PNG      = os.path.join(OUTPUT_DIR, "avatar.png")
JOINTS_JSON     = os.path.join(OUTPUT_DIR, "joints.json")
SEG_NPZ         = os.path.join(OUTPUT_DIR, "segmentation.npz")


def check_dependencies():
    """Warn if required libraries are missing."""
    missing = []
    for pkg in ["trimesh", "torch", "numpy", "PIL", "scipy"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("[!] Missing packages:", ", ".join(missing))
        print("    Install with: pip install", " ".join(missing).replace("PIL", "pillow"))
        sys.exit(1)


def run_pipeline(glb_path: str):
    """Full Part 1 pipeline."""

    print("=" * 60)
    print("  HUMAN BODY AI PIPELINE — prototype v0.1")
    print("=" * 60)

    # ── Step 1: Parse GLB ────────────────────────────────────────────────────
    print("\n[Step 1] Parsing GLB mesh...")
    from glb_parser import parse_glb
    mesh_data = parse_glb(glb_path)
    vertices  = mesh_data["vertices"]
    normals   = mesh_data["normals"]
    mesh      = mesh_data["mesh"]

    # ── Step 2: Train MLP (skipped if already trained) ───────────────────────
    print("\n[Step 2] Body-part MLP training...")
    from mesh_segment import train_mlp
    if os.path.exists(MODEL_SAVE_PATH):
        print("  Model already exists. Skipping training.")
        print(f"  Delete {MODEL_SAVE_PATH} to retrain.")
    else:
        train_mlp(CAPE_DATA_DIR, MODEL_SAVE_PATH, epochs=40)

    # ── Step 3: Segment mesh ─────────────────────────────────────────────────
    print("\n[Step 3] Segmenting mesh into body parts...")
    from mesh_segment import segment_mesh, render_avatar_sprite
    labels = segment_mesh(vertices, normals, MODEL_SAVE_PATH)

    # ── Step 4: Save sprite ───────────────────────────────────────────────────
    print("\n[Step 4] Rendering avatar sprite...")
    render_avatar_sprite(vertices, labels, AVATAR_PNG, size=128)

    # ── Step 5: Extract skeleton ─────────────────────────────────────────────
    print("\n[Step 5] Extracting skeleton joints...")
    from skeleton_extract import extract_joints, joints_to_proportions, save_joints
    joints = extract_joints(vertices, labels)
    props  = joints_to_proportions(joints)
    save_joints(joints, props, JOINTS_JSON)

    # ── Step 6: Save clean mesh + segmentation ────────────────────────────────
    print("\n[Step 6] Saving outputs...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    np.savez(SEG_NPZ, vertices=vertices, normals=normals, labels=labels)
    print(f"  Segmentation → {SEG_NPZ}")

    # Export clean GLB
    clean_glb = os.path.join(OUTPUT_DIR, "clean_mesh.glb")
    mesh.export(clean_glb)
    print(f"  Clean mesh   → {clean_glb}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  DONE. Outputs:")
    print(f"    Avatar sprite  : {AVATAR_PNG}")
    print(f"    Joints JSON    : {JOINTS_JSON}")
    print(f"    Segmentation   : {SEG_NPZ}")
    print(f"    Clean mesh GLB : {clean_glb}")
    print("\n  Next step: run  python ../game/main.py")
    print("=" * 60)


if __name__ == "__main__":
    check_dependencies()
    glb_path = sys.argv[1] if len(sys.argv) > 1 else GLB_INPUT_PATH

    if not os.path.exists(glb_path):
        print(f"\n[ERROR] GLB file not found: {glb_path}")
        print("  Set GLB_INPUT_PATH at the top of this file, or pass it as an argument.")
        sys.exit(1)

    run_pipeline(glb_path)
