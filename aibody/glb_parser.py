"""
glb_parser.py
-------------
Loads a GLB (binary GLTF) file and extracts:
  - vertices (Nx3 float array)
  - normals  (Nx3 float array)
  - faces    (Mx3 int array)
  - a centred + normalised copy ready for ML

Install:
    pip install trimesh numpy pygltflib
"""

import numpy as np
import trimesh
import json
import os

# ── Path placeholder ─────────────────────────────────────────────────────────
# Change this to your actual GLB file path
DEFAULT_GLB_PATH = r"C:/Users/YourName/project/input_model.glb"


def load_glb(glb_path: str) -> trimesh.Trimesh:
    """Load a GLB file and return a single merged Trimesh."""
    print(f"[glb_parser] Loading: {glb_path}")

    scene = trimesh.load(glb_path, force="scene")

    # If the file has multiple meshes, merge them all into one
    if isinstance(scene, trimesh.Scene):
        meshes = [g for g in scene.geometry.values()
                  if isinstance(g, trimesh.Trimesh)]
        if not meshes:
            raise ValueError("No triangle meshes found in the GLB file.")
        mesh = trimesh.util.concatenate(meshes)
    else:
        mesh = scene

    print(f"[glb_parser] Vertices: {len(mesh.vertices):,}  Faces: {len(mesh.faces):,}")
    return mesh


def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """
    Basic cleanup:
      - remove duplicate/degenerate faces
      - fill small holes
      - re-compute normals
    """
    try:
        mesh.remove_duplicate_faces()
    except AttributeError:
        mesh.update_faces(mesh.unique_faces())
    try:
        mesh.remove_degenerate_faces()
    except AttributeError:
        mesh.update_faces(mesh.nondegenerate_faces())
    mesh.fill_holes()
    mesh.fix_normals()
    print(f"[glb_parser] After cleanup — Vertices: {len(mesh.vertices):,}  Faces: {len(mesh.faces):,}")
    return mesh


def normalise_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """
    Centre mesh at origin and scale so it fits in a unit cube.
    This makes geometry heuristics (head at top, feet at bottom) reliable.
    """
    centre = mesh.bounds.mean(axis=0)          # midpoint of bounding box
    mesh.vertices -= centre                     # translate to origin

    scale = mesh.bounds[1].max() - mesh.bounds[0].min()   # longest axis span
    if scale > 0:
        mesh.vertices /= scale                 # scale to [-0.5, 0.5] range

    return mesh


def extract_data(mesh: trimesh.Trimesh) -> dict:
    """
    Return a dictionary with numpy arrays for the rest of the pipeline.
    """
    return {
        "vertices": np.array(mesh.vertices, dtype=np.float32),   # (N, 3)
        "normals":  np.array(mesh.vertex_normals, dtype=np.float32),  # (N, 3)
        "faces":    np.array(mesh.faces, dtype=np.int32),         # (M, 3)
    }


def parse_glb(glb_path: str) -> dict:
    """Main entry point: load → clean → normalise → extract."""
    mesh = load_glb(glb_path)
    mesh = clean_mesh(mesh)
    mesh = normalise_mesh(mesh)
    data = extract_data(mesh)
    data["mesh"] = mesh   # keep the trimesh object too
    return data


# ── CLI quick-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GLB_PATH
    if not os.path.exists(path):
        print(f"File not found: {path}")
        print("Usage: python glb_parser.py path/to/model.glb")
    else:
        data = parse_glb(path)
        print(f"Vertices shape : {data['vertices'].shape}")
        print(f"Normals shape  : {data['normals'].shape}")
        print(f"Faces shape    : {data['faces'].shape}")
        print(f"Y range        : {data['vertices'][:,1].min():.3f} → {data['vertices'][:,1].max():.3f}")
