"""
skeleton_extract.py
-------------------
Takes the segmented vertex data and computes simplified skeleton joint positions:
    - head centre
    - neck
    - left/right shoulder
    - left/right elbow
    - left/right wrist
    - pelvis
    - left/right knee
    - left/right ankle

Outputs: outputs/joints.json

Run:
    python skeleton_extract.py

Install:
    pip install numpy scipy
"""

import numpy as np
import json
import os

# ── Paths ─────────────────────────────────────────────────────────────────────
SEG_NPZ_PATH   = r"C:/Users/YourName/project/outputs/segmentation.npz"
JOINTS_OUT     = r"C:/Users/YourName/project/outputs/joints.json"

# Body-part label IDs (must match mesh_segment.py)
HEAD      = 0
TORSO     = 1
LEFT_ARM  = 2
RIGHT_ARM = 3
LEGS      = 4


def region_vertices(vertices: np.ndarray, labels: np.ndarray, part_id: int):
    """Return vertices belonging to a single body part."""
    mask = labels == part_id
    if mask.sum() == 0:
        return None
    return vertices[mask]


def centroid(verts: np.ndarray) -> np.ndarray:
    """3D centroid of a vertex cloud."""
    return verts.mean(axis=0)


def percentile_point(verts: np.ndarray, axis: int, pct: float) -> np.ndarray:
    """
    Return the centroid of vertices near a percentile along one axis.
    Useful for finding 'top of head', 'bottom of foot', etc.
    """
    threshold = np.percentile(verts[:, axis], pct)
    # Take the top/bottom 5% of vertices near that threshold
    band = np.abs(verts[:, axis] - threshold) < 0.05
    if band.sum() == 0:
        band = np.ones(len(verts), dtype=bool)
    return verts[band].mean(axis=0)


def extract_joints(vertices: np.ndarray, labels: np.ndarray) -> dict:
    """
    Compute all joint positions from segmented vertex regions.
    Returns a dict: joint_name → [x, y, z]
    """
    joints = {}

    # ── Head & Neck ───────────────────────────────────────────────────────────
    head_verts = region_vertices(vertices, labels, HEAD)
    torso_verts = region_vertices(vertices, labels, TORSO)

    if head_verts is not None:
        joints["head"] = centroid(head_verts).tolist()
        joints["neck"] = percentile_point(head_verts, axis=1, pct=5).tolist()

    # ── Torso ─────────────────────────────────────────────────────────────────
    if torso_verts is not None:
        joints["chest"]  = percentile_point(torso_verts, axis=1, pct=80).tolist()
        joints["pelvis"] = percentile_point(torso_verts, axis=1, pct=10).tolist()

    # ── Arms ──────────────────────────────────────────────────────────────────
    for side, part_id in [("left", LEFT_ARM), ("right", RIGHT_ARM)]:
        arm_verts = region_vertices(vertices, labels, part_id)
        if arm_verts is None:
            continue

        # Shoulder = top of arm region, near torso
        shoulder_idx = arm_verts[:, 1].argmax()
        joints[f"{side}_shoulder"] = arm_verts[shoulder_idx].tolist()

        # Wrist = bottom/far end of arm
        wrist_idx = arm_verts[:, 1].argmin()
        joints[f"{side}_wrist"] = arm_verts[wrist_idx].tolist()

        # Elbow = midpoint between shoulder and wrist
        sh = np.array(joints[f"{side}_shoulder"])
        wr = np.array(joints[f"{side}_wrist"])
        joints[f"{side}_elbow"] = ((sh + wr) / 2).tolist()

    # ── Legs ──────────────────────────────────────────────────────────────────
    leg_verts = region_vertices(vertices, labels, LEGS)
    if leg_verts is not None:
        # Split legs by X axis: negative = left, positive = right
        left_leg  = leg_verts[leg_verts[:, 0] < 0]
        right_leg = leg_verts[leg_verts[:, 0] >= 0]

        for side, verts_side in [("left", left_leg), ("right", right_leg)]:
            if len(verts_side) == 0:
                continue

            hip_idx   = verts_side[:, 1].argmax()
            ankle_idx = verts_side[:, 1].argmin()

            hip    = verts_side[hip_idx]
            ankle  = verts_side[ankle_idx]
            knee   = (hip + ankle) / 2   # approximate midpoint

            joints[f"{side}_hip"]   = hip.tolist()
            joints[f"{side}_knee"]  = knee.tolist()
            joints[f"{side}_ankle"] = ankle.tolist()

    return joints


def joints_to_proportions(joints: dict) -> dict:
    """
    Convert 3D joints into 2D proportions (0–1 normalised) for the sprite renderer.
    Useful for the game's player.py to know body proportions.
    """
    if not joints:
        return {}

    all_pts = np.array(list(joints.values()))
    x_min, y_min = all_pts[:, 0].min(), all_pts[:, 1].min()
    x_max, y_max = all_pts[:, 0].max(), all_pts[:, 1].max()

    props = {}
    for name, pt in joints.items():
        nx = (pt[0] - x_min) / (x_max - x_min + 1e-8)
        # Flip Y so 1 = top
        ny = 1.0 - (pt[1] - y_min) / (y_max - y_min + 1e-8)
        props[name] = {"x": round(nx, 4), "y": round(ny, 4)}

    return props


def save_joints(joints: dict, proportions: dict, out_path: str):
    """Save joints to a JSON file."""
    payload = {
        "joints_3d": {k: [round(v, 5) for v in vals]
                      for k, vals in joints.items()},
        "joints_2d_normalised": proportions,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[skeleton] Joints saved → {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not os.path.exists(SEG_NPZ_PATH):
        print(f"Segmentation file not found: {SEG_NPZ_PATH}")
        print("Run mesh_segment.py first.")
    else:
        data = np.load(SEG_NPZ_PATH)
        vertices = data["vertices"]
        labels   = data["labels"]

        print("[skeleton] Extracting joints...")
        joints = extract_joints(vertices, labels)
        props  = joints_to_proportions(joints)

        print("\nJoints found:")
        for name, pos in joints.items():
            print(f"  {name:20s}: {[round(v,3) for v in pos]}")

        save_joints(joints, props, JOINTS_OUT)
