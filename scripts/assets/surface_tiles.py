"""Original, seamless surface maps for the EIDOLON asset review."""

from functools import lru_cache
from io import BytesIO

import numpy as np
from PIL import Image


def lattice(size, columns, rows, seed):
    random = np.random.default_rng(seed)
    field = random.random((rows, columns), dtype=np.float32)
    x = np.arange(size, dtype=np.float32) * columns / size
    y = np.arange(size, dtype=np.float32) * rows / size
    i, j = x.astype(int), y.astype(int)
    u, v = x - i, y - j
    u, v = u * u * (3 - 2 * u), v * v * (3 - 2 * v)
    i_next, j_next = (i + 1) % columns, (j + 1) % rows
    near = field[j[:, None], i] * (1 - u) + field[j[:, None], i_next] * u
    far = field[j_next[:, None], i] * (1 - u) + field[j_next[:, None], i_next] * u
    return (near * (1 - v[:, None]) + far * v[:, None]).astype(np.float32)


def cellular_seams(size, count, seed):
    random = np.random.default_rng(seed)
    sites = random.uniform(.19, .81, (count, count, 2)).astype(np.float32)
    coord = np.arange(size, dtype=np.float32) * count / size
    index = coord.astype(int)
    one = np.full((size, size), np.inf, dtype=np.float32)
    two = one.copy()
    for row in (-1, 0, 1):
        for column in (-1, 0, 1):
            near = sites[(index[:, None] + row) % count, (index + column) % count]
            dx = index + column + near[:, :, 0] - coord
            dy = index[:, None] + row + near[:, :, 1] - coord[:, None]
            distance = dx * dx + dy * dy
            two = np.minimum(two, np.maximum(one, distance))
            one = np.minimum(one, distance)
    return np.exp(-np.square((np.sqrt(two) - np.sqrt(one)) * 16))


def encode(values, jpeg=False):
    pixels = np.uint8(np.clip(values, 0, 1) * 255 + .5)
    image = Image.fromarray(pixels)
    output = BytesIO()
    if jpeg:
        image.save(output, format="JPEG", quality=94, subsampling=0)
    else:
        image.save(output, format="PNG", compress_level=3)
    return output.getvalue()


@lru_cache(maxsize=40)
def render_maps(family, size, original_roughness, original_metalness):
    """Return color (sRGB), tangent normal and glTF packed roughness/metal."""
    cloud = lattice(size, 9, 11, 510)
    grit = lattice(size, 131, 127, 982)
    speckle = lattice(size, 389, 397, 803)
    rust = np.zeros_like(cloud)
    relief = .68 * grit + .32 * speckle
    brightness = .75 + .22 * cloud
    roughness = np.clip(original_roughness + .18 * (grit - .5), .07, .98)
    metalness = np.full_like(cloud, original_metalness)
    if family in ("bark", "wood", "rope"):
        fiber = lattice(size, 91, 9, 76) * .68 + lattice(size, 198, 21, 919) * .32
        split = np.clip((lattice(size, 23, 3, 126) + .22 * fiber - .72) * 4.1, 0, 1)
        relief = .57 * fiber - .26 * split + .12 * grit
        brightness = .71 + .25 * fiber - .34 * split + .09 * cloud
        roughness = .63 + .26 * cloud - .17 * fiber
    elif family in ("stone", "bone"):
        seam = cellular_seams(size, 11 if family == "stone" else 23, 101)
        stratum = lattice(size, 7, 63, 341)
        relief = .18 * grit + .29 * stratum - .27 * seam + .19 * speckle
        brightness = .65 + .18 * stratum + .16 * cloud + .11 * grit - .24 * seam
        roughness = .58 + .33 * grit + .09 * seam
    elif family in ("iron", "bronze"):
        scrape = lattice(size, 231, 19, 887)
        rust = np.clip((.62 * cloud + .38 * grit - .48) * (3.2 if family == "bronze" else 2.7), 0, .76)
        relief = .36 * scrape + .23 * speckle - .24 * rust
        brightness = .74 + .20 * scrape + .14 * cloud - .36 * rust
        roughness = np.clip(original_roughness - .13 + .44 * rust + .17 * scrape, .11, .88)
        metalness = np.clip(original_metalness * (1 - .82 * rust), 0, 1)
    elif family in ("hide", "chitin", "leather"):
        pore = cellular_seams(size, 29 if family == "chitin" else 49, 233)
        wrinkle = lattice(size, 53, 19, 821)
        relief = .39 * wrinkle + .19 * speckle - .24 * pore
        brightness = .73 + .22 * wrinkle + .13 * cloud - .21 * pore
        roughness = np.clip(original_roughness - .06 + .25 * pore + .15 * grit, .23, .93)
    elif family == "foliage":
        vein = lattice(size, 35, 108, 421)
        relief = .34 * vein + .13 * speckle
        brightness = .73 + .15 * vein + .20 * cloud
        roughness = .53 + .28 * cloud

    color = np.repeat(np.clip(brightness, .33, 1)[..., None], 3, axis=2)
    if family == "iron":
        color *= 1 + rust[..., None] * np.array([.18, -.16, -.29])
    if family == "bronze":
        color *= 1 + rust[..., None] * np.array([-.17, .19, .08])
    # Centered differences wrap at both edges, providing a periodic tangent map.
    du = np.roll(relief, -1, axis=1) - np.roll(relief, 1, axis=1)
    dv = np.roll(relief, -1, axis=0) - np.roll(relief, 1, axis=0)
    normal = np.stack((-du * 2.9, dv * 2.9, np.ones_like(relief)), axis=2)
    normal /= np.linalg.norm(normal, axis=2)[..., None]
    packed = np.stack((np.ones_like(roughness), roughness, metalness), axis=2)
    return encode(color, jpeg=True), encode(normal * .5 + .5), encode(packed)
