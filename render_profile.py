import os
import numpy as np
import trimesh
from PIL import Image, ImageDraw

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = r"C:/Users/nisha/Downloads/files (2) (1)"

GLB_PATH       = os.path.join(BASE_DIR, "4_15_2026.glb")
OUTPUT_AVATAR  = os.path.join(BASE_DIR, "outputs", "avatar.png")

SPRITE_W = 280
SPRITE_H = 420


def load_mesh():
    print("[render] Loading GLB...")
    mesh = trimesh.load(GLB_PATH)

    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    print(f"[render] Loaded: {len(mesh.vertices)} verts, {len(mesh.faces)} faces")
    return mesh


def isolate_person(mesh):
    """
    Split into connected mesh components and choose the one
    most likely to be the human body.
    """
    print("[render] Splitting connected components...")

    components = mesh.split(only_watertight=False)
    if not components:
        print("[render] No components found; using full mesh.")
        return mesh

    scene_center = mesh.centroid
    best_score = -1e9
    best = None

    for i, comp in enumerate(components):
        if len(comp.vertices) < 50:
            continue

        bounds = comp.bounds
        size = bounds[1] - bounds[0]

        width  = size[0]
        depth  = size[1]
        height = size[2]

        # Basic filters to reject floor / walls
        if height < 0.3:
            continue

        # density: verts per volume-ish
        volume_like = max(width * depth * height, 1e-6)
        density = len(comp.vertices) / volume_like

        # prefer center-ish chunks
        dist_to_center = np.linalg.norm(comp.centroid[:2] - scene_center[:2])

        # score:
        # + tall
        # + dense
        # - far from center
        score = (
            height * 5.0 +
            density * 0.01 -
            dist_to_center * 2.0
        )

        print(
            f"  comp {i}: verts={len(comp.vertices)} "
            f"h={height:.2f} density={density:.1f} score={score:.2f}"
        )

        if score > best_score:
            best_score = score
            best = comp

    if best is None:
        print("[render] No suitable component found; using full mesh.")
        return mesh

    print(
        f"[render] Selected component: "
        f"{len(best.vertices)} verts, {len(best.faces)} faces"
    )

    return best


def render_side_profile(mesh):
    """
    Render solid coloured side profile by triangle fill.
    """
    print("[render] Rendering side profile...")

    verts = mesh.vertices.copy()

    # Rotate to side view
    rot = trimesh.transformations.rotation_matrix(
        np.radians(90), [0, 1, 0]
    )
    verts = trimesh.transform_points(verts, rot)

    # Project X/Z plane
    x = verts[:, 0]
    y = -verts[:, 2]

    # Normalize to sprite
    x = (x - x.min()) / (x.max() - x.min() + 1e-8)
    y = (y - y.min()) / (y.max() - y.min() + 1e-8)

    x = x * (SPRITE_W * 0.75) + SPRITE_W * 0.125
    y = y * (SPRITE_H * 0.80) + SPRITE_H * 0.10

    img = Image.new("RGBA", (SPRITE_W, SPRITE_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # vertex colors if present
    colours = None
    try:
        vc = mesh.visual.vertex_colors[:, :3]
        if len(vc) == len(mesh.vertices):
            colours = vc
    except:
        colours = None

    # depth sort triangles
    depth = verts[:, 1]
    face_depths = []

    for idx, face in enumerate(mesh.faces):
        d = np.mean(depth[face])
        face_depths.append((d, idx))

    face_depths.sort()

    for _, idx in face_depths:
        face = mesh.faces[idx]

        pts = [
            (x[face[0]], y[face[0]]),
            (x[face[1]], y[face[1]]),
            (x[face[2]], y[face[2]])
        ]

        if colours is not None:
            c = np.mean(colours[face], axis=0)
            colour = (
                int(c[0]),
                int(c[1]),
                int(c[2]),
                230
            )
        else:
            colour = (80, 170, 230, 230)

        draw.polygon(pts, fill=colour)

    return img


def autocrop(img):
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    img.thumbnail((SPRITE_W, SPRITE_H), Image.LANCZOS)

    final = Image.new("RGBA", (SPRITE_W, SPRITE_H), (0, 0, 0, 0))
    x = (SPRITE_W - img.width) // 2
    y = (SPRITE_H - img.height) // 2

    final.paste(img, (x, y))
    return final


def save_avatar(img):
    os.makedirs(os.path.dirname(OUTPUT_AVATAR), exist_ok=True)
    img.save(OUTPUT_AVATAR)
    print(f"[render] Saved avatar → {OUTPUT_AVATAR}")


def main():
    mesh = load_mesh()
    person = isolate_person(mesh)
    img = render_side_profile(person)
    img = autocrop(img)
    save_avatar(img)


if __name__ == "__main__":
    main()