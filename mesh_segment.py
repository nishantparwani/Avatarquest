"""
mesh_segment.py
---------------
Segments a human mesh into 5 body regions:
    0 = head
    1 = torso
    2 = left arm
    3 = right arm
    4 = legs

Strategy: geometric heuristics first (height bands + lateral position),
then an optional lightweight MLP trained on CAPE data to refine.

Run standalone to produce outputs/avatar.png and outputs/joints.json:
    python mesh_segment.py

Install:
    pip install trimesh numpy torch pillow
"""

import numpy as np
import os
import json
import torch
import torch.nn as nn
from PIL import Image, ImageDraw

# ── Paths ─────────────────────────────────────────────────────────────────────
CAPE_DATA_DIR  = r"C:/Users/YourName/project/ai_body/cape_data/00096"
MODEL_SAVE_PATH = r"C:/Users/YourName/project/ai_body/models/body_classifier.pt"
OUTPUT_DIR      = r"C:/Users/YourName/project/outputs"

# Body-part labels and colours for visualisation
LABELS = {0: "head", 1: "torso", 2: "left_arm", 3: "right_arm", 4: "legs"}
COLOURS = {
    0: (230, 100, 100),   # red-ish  — head
    1: (100, 180, 230),   # blue     — torso
    2: (100, 230, 130),   # green    — left arm
    3: (230, 200,  80),   # yellow   — right arm
    4: (180, 100, 230),   # purple   — legs
}


# ── Lightweight MLP ───────────────────────────────────────────────────────────
class BodyPartMLP(nn.Module):
    """
    Input:  6 features  (x, y, z, nx, ny, nz)
    Output: 5 classes   (head, torso, l-arm, r-arm, legs)

    Small on purpose — runs on CPU in seconds.
    """
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(6, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 5),
        )

    def forward(self, x):
        return self.net(x)


# ── Geometric heuristics ──────────────────────────────────────────────────────
def heuristic_labels(vertices: np.ndarray) -> np.ndarray:
    """
    Fast rule-based segmentation on a NORMALISED mesh (Y is up, range ~0-1).

    After normalise_mesh(), the mesh sits in [-0.5, 0.5].
    We shift Y to [0, 1] for readable thresholds.
    """
    N = len(vertices)
    labels = np.zeros(N, dtype=np.int64)

    x = vertices[:, 0]   # left(-) / right(+)
    y = vertices[:, 1]   # bottom(-0.5) / top(+0.5)
    # shift Y to 0-1
    y_norm = (y - y.min()) / (y.max() - y.min() + 1e-8)

    # ── height bands ─────────────────────────────
    # head:    top 15 %
    # torso:   55 % – 85 %
    # arms:    40 % – 85 % BUT laterally extended
    # legs:    bottom 40 %

    head_mask  = y_norm > 0.85
    torso_mask = (y_norm >= 0.55) & (y_norm <= 0.85)
    leg_mask   = y_norm < 0.40

    # Arms are at torso height but their x-extent is wider than the torso core.
    # Estimate "shoulder width" from the 70-85% height band
    shoulder_band = (y_norm >= 0.70) & (y_norm <= 0.85)
    if shoulder_band.sum() > 10:
        torso_x_max = np.percentile(np.abs(x[shoulder_band]), 60)
    else:
        torso_x_max = 0.12   # fallback

    arm_mask = (
        (y_norm >= 0.40) & (y_norm <= 0.85) &
        (np.abs(x) > torso_x_max * 1.1)
    )
    left_arm_mask  = arm_mask & (x < 0)
    right_arm_mask = arm_mask & (x >= 0)

    # Assign in order (later wins on overlap)
    labels[leg_mask]        = 4
    labels[torso_mask]      = 1
    labels[left_arm_mask]   = 2
    labels[right_arm_mask]  = 3
    labels[head_mask]       = 0

    return labels


# ── MLP training on CAPE data ─────────────────────────────────────────────────
def load_cape_sample(cape_dir: str):
    """
    CAPE dataset stores per-frame posed meshes as .npz files.
    We expect at least one .npz with keys: 'v_posed' or 'vertices'.

    Returns (vertices, normals) as numpy arrays, or None if not found.
    """
    import glob
    npz_files = glob.glob(os.path.join(cape_dir, "**", "*.npz"), recursive=True)
    if not npz_files:
        print(f"[mesh_segment] No .npz files found in {cape_dir}")
        return None, None

    all_verts = []
    all_norms = []

    for fpath in npz_files[:5]:   # limit to 5 frames for speed
        data = np.load(fpath, allow_pickle=True)

        # Try different key names CAPE uses across versions
        verts = None
        for key in ("v_posed", "vertices", "verts"):
            if key in data:
                verts = data[key].astype(np.float32)
                break
        if verts is None:
            continue

        # Normalise each frame
        verts -= verts.mean(axis=0)
        scale = np.abs(verts).max()
        if scale > 0:
            verts /= scale

        # Estimate normals if not present
        import trimesh as tm
        m = tm.Trimesh(vertices=verts)
        norms = np.array(m.vertex_normals, dtype=np.float32)

        all_verts.append(verts)
        all_norms.append(norms)

    if not all_verts:
        return None, None

    return np.concatenate(all_verts), np.concatenate(all_norms)


def train_mlp(cape_dir: str, save_path: str, epochs: int = 30):
    """
    Train the MLP using heuristic labels on CAPE data as pseudo ground-truth.
    This is a self-supervised approach — no manual annotation needed.
    """
    print("[mesh_segment] Loading CAPE data for training...")
    verts, norms = load_cape_sample(cape_dir)

    if verts is None:
        print("[mesh_segment] CAPE data not found. Using heuristics only (no MLP training).")
        return

    pseudo_labels = heuristic_labels(verts)

    # Features: position + normal
    X = np.concatenate([verts, norms], axis=1).astype(np.float32)  # (N, 6)
    Y = pseudo_labels.astype(np.int64)

    # Subsample to keep training fast (10 000 points max)
    if len(X) > 10000:
        idx = np.random.choice(len(X), 10000, replace=False)
        X, Y = X[idx], Y[idx]

    X_t = torch.tensor(X)
    Y_t = torch.tensor(Y)

    model = BodyPartMLP()
    optim = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()

    print(f"[mesh_segment] Training on {len(X_t):,} points for {epochs} epochs...")
    for ep in range(1, epochs + 1):
        logits = model(X_t)
        loss = loss_fn(logits, Y_t)
        optim.zero_grad()
        loss.backward()
        optim.step()
        if ep % 10 == 0:
            acc = (logits.argmax(1) == Y_t).float().mean().item()
            print(f"  Epoch {ep:3d}  loss={loss.item():.4f}  acc={acc:.3f}")

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"[mesh_segment] Model saved → {save_path}")


# ── Inference ─────────────────────────────────────────────────────────────────
def segment_mesh(vertices: np.ndarray, normals: np.ndarray,
                 model_path: str = None) -> np.ndarray:
    """
    Returns per-vertex label array (int64, values 0-4).
    Uses MLP if model_path exists, otherwise falls back to heuristics.
    """
    if model_path and os.path.exists(model_path):
        print("[mesh_segment] Using trained MLP for segmentation.")
        model = BodyPartMLP()
        model.load_state_dict(torch.load(model_path, map_location="cpu"))
        model.eval()

        X = np.concatenate([vertices, normals], axis=1).astype(np.float32)
        with torch.no_grad():
            logits = model(torch.tensor(X))
        labels = logits.argmax(1).numpy()
    else:
        print("[mesh_segment] Using geometric heuristics for segmentation.")
        labels = heuristic_labels(vertices)

    # Print summary
    for part_id, name in LABELS.items():
        count = (labels == part_id).sum()
        print(f"  {name:12s}: {count:6,} vertices")

    return labels


# ── Visualisation ──────────────────────────────────────────────────────────────
def render_avatar_sprite(vertices: np.ndarray, labels: np.ndarray,
                         out_path: str, size: int = 128):
    """
    Project the 3D mesh onto 2D (XY plane = side view) and draw a
    coloured pixel sprite. Saved as a PNG for the game.
    """
    # Use X and Y (front view). Flip Y so head is up.
    xs = vertices[:, 0]
    ys = -vertices[:, 1]   # flip so +Y = up in image

    # Normalise to [0, size]
    def norm_axis(arr):
        mn, mx = arr.min(), arr.max()
        return (arr - mn) / (mx - mn + 1e-8) * (size - 4) + 2

    xs_img = norm_axis(xs).astype(int)
    ys_img = norm_axis(ys).astype(int)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pix = img.load()

    for i in range(len(vertices)):
        px, py = xs_img[i], ys_img[i]
        if 0 <= px < size and 0 <= py < size:
            r, g, b = COLOURS[labels[i]]
            pix[px, py] = (r, g, b, 255)

    # Upscale for a chunky pixel look
    img = img.resize((size * 2, size * 2), Image.NEAREST)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path)
    print(f"[mesh_segment] Avatar sprite saved → {out_path}")
    return img


# ── Main pipeline ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from glb_parser import parse_glb

    GLB_PATH = r"C:/Users/YourName/project/input_model.glb"

    # 1. Parse GLB
    data = parse_glb(GLB_PATH)
    verts   = data["vertices"]
    normals = data["normals"]

    # 2. (Optional) train MLP on CAPE data if not already trained
    if not os.path.exists(MODEL_SAVE_PATH):
        train_mlp(CAPE_DATA_DIR, MODEL_SAVE_PATH)

    # 3. Segment
    labels = segment_mesh(verts, normals, MODEL_SAVE_PATH)

    # 4. Save avatar sprite
    avatar_path = os.path.join(OUTPUT_DIR, "avatar.png")
    render_avatar_sprite(verts, labels, avatar_path)

    # 5. Save raw label data alongside vertices for skeleton step
    seg_out = os.path.join(OUTPUT_DIR, "segmentation.npz")
    np.savez(seg_out, vertices=verts, normals=normals, labels=labels)
    print(f"[mesh_segment] Segmentation saved → {seg_out}")
