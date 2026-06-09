from pathlib import Path
import argparse
import csv
import math

import numpy as np
from PIL import Image


def Normalize(vector):
    length = np.linalg.norm(vector)

    if length == 0:
        raise ValueError("Cannot normalize zero-length vector")

    return vector / length

def SrgbToLinear(x):
    return np.where(
        x <= 0.04045,
        x / 12.92,
        ((x + 0.055) / 1.055) ** 2.4
    )

def LinearToSrgb(x):
    return np.where(
        x <= 0.0031308,
        x * 12.92,
        1.055 * (x ** (1.0 / 2.4)) - 0.055
    )

def WriteBinaryPly(path, points, colors, faces = None):
    path = Path(path)

    points = np.asarray(points, dtype = np.float32)
    colors = np.asarray(colors)

    if faces is None:
        faces = []

    faces = np.asarray(faces, dtype = np.int32)

    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must be shaped (N, 3)")

    if colors.ndim != 2 or colors.shape[1] < 3:
        raise ValueError("colors must be shaped (N, 3) or (N, 4)")

    colors = colors[:, :3]

    if colors.dtype != np.uint8:
        colors = np.clip(colors, 0, 255).astype(np.uint8)

    if len(points) != len(colors):
        raise ValueError("points and colors must have the same length")

    if faces.size > 0:
        if faces.ndim != 2 or faces.shape[1] != 3:
            raise ValueError("faces must be shaped (M, 3)")

        if faces.min() < 0 or faces.max() >= len(points):
            raise ValueError("faces contain invalid vertex indices")
    else:
        faces = np.empty((0, 3), dtype = np.int32)

    vertexCount = len(points)
    faceCount = len(faces)

    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {vertexCount}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        f"element face {faceCount}\n"
        "property list uchar int vertex_indices\n"
        "end_header\n"
    ).encode("ascii")

    vertexData = np.empty(
        vertexCount,
        dtype = [
            ("x", "<f4"),
            ("y", "<f4"),
            ("z", "<f4"),
            ("red", "u1"),
            ("green", "u1"),
            ("blue", "u1"),
        ]
    )

    vertexData["x"] = points[:, 0]
    vertexData["y"] = points[:, 1]
    vertexData["z"] = points[:, 2]
    vertexData["red"] = colors[:, 0]
    vertexData["green"] = colors[:, 1]
    vertexData["blue"] = colors[:, 2]

    faceData = np.empty(
        faceCount,
        dtype = [
            ("vertexCount", "u1"),
            ("v0", "<i4"),
            ("v1", "<i4"),
            ("v2", "<i4"),
        ]
    )

    if faceCount > 0:
        faceData["vertexCount"] = 3
        faceData["v0"] = faces[:, 0]
        faceData["v1"] = faces[:, 1]
        faceData["v2"] = faces[:, 2]

    with open(path, "wb") as file:
        file.write(header)
        vertexData.tofile(file)
        faceData.tofile(file)

def ReadSetups(path):
    names = []
    positions = []
    interests = []
    fovs = []
    nearClips = []
    farClips = []

    current = {}

    with open(path, "r", encoding = "utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            parts = line.split()

            key = parts[0]

            if key == "setup":
                if current:
                    names.append(current["name"])
                    positions.append(current["position"])
                    interests.append(current["interest"])
                    fovs.append(current["fov"])
                    nearClips.append(current["nclip"])
                    farClips.append(current["fclip"])

                current = {}

            elif key == "background":
                current["name"] = parts[1].rsplit(".", 1)[0]

            elif key == "position":
                current["position"] = (
                    float(parts[1]),
                    float(parts[2]),
                    float(parts[3])
                )

            elif key == "interest":
                current["interest"] = (
                    float(parts[1]),
                    float(parts[2]),
                    float(parts[3])
                )

            elif key == "fov":
                current["fov"] = float(parts[1])

            elif key == "nclip":
                current["nclip"] = float(parts[1])

            elif key == "fclip":
                current["fclip"] = float(parts[1])

    if current:
        names.append(current["name"])
        positions.append(current["position"])
        interests.append(current["interest"])
        fovs.append(current["fov"])
        nearClips.append(current["nclip"])
        farClips.append(current["fclip"])

    return (
        names,
        positions,
        interests,
        fovs,
        nearClips,
        farClips
    )

def BuildTransformationMatrix(position, lookAt):
    position = np.asarray(position, dtype=float)
    lookAt = np.asarray(lookAt, dtype=float)

    forward = Normalize(lookAt - position)

    worldUp = np.array([0.0, 0.0, 1.0])

    if abs(np.dot(forward, worldUp)) > 0.999:
        worldUp = np.array([0.0, 1.0, 0.0])

    right = Normalize(np.cross(forward, worldUp))
    up = Normalize(np.cross(right, forward))

    matrix = np.eye(4)

    matrix[0:3, 0] = right
    matrix[0:3, 1] = up
    matrix[0:3, 2] = -forward
    matrix[0:3, 3] = position

    return matrix

def LoadDepthCsv(csvPath, width, height):
    depth = np.zeros((height, width), dtype=np.uint16)

    with open(csvPath, newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            x = int(row["x"])
            y = int(row["y"])
            value = int(row["value"])

            if 0 <= x < width and 0 <= y < height:
                depth[y, x] = value

    return depth

def DecodeDepth(rawDepth, depthNear, depthFar):
    glDepth = 0xffff - ((rawDepth * 0x10000) // 100 // (0x10000 - rawDepth))
    glDepth = glDepth / 65535.0

    zNdc = glDepth * 2.0 - 1.0

    return (2.0 * depthNear * depthFar) / (
        depthFar + depthNear - zNdc * (depthFar - depthNear)
    )

def ProjectPoints(
    depthCsvPath,
    backgroundPath,
    position,
    lookAt,
    fovDegrees,
    depthNear,
    depthFar,
    gamma,
    maxDepth,
    depthSkip,
    pointsOnly,
):
    backgroundImage = Image.open(backgroundPath).convert("RGB")
    background = np.array(backgroundImage)

    if gamma != 0:
        background = background.astype(np.float32) / 255.0
        background = SrgbToLinear(background)
        background = np.power(background, 1.0 / gamma)
        background = LinearToSrgb(background)
        background = np.clip(background * 255.0, 0, 255).astype(np.uint8)

    height, width = background.shape[:2]

    depthRaw = LoadDepthCsv(depthCsvPath, width, height).astype(np.float64)

    vertexIndex = np.full((height, width), -1, dtype=np.int32)

    points = []
    colors = []
    depths = np.full((height, width), np.nan, dtype=np.float32)

    hfov = math.radians(fovDegrees)
    aspect = width / height
    vfov = 2.0 * math.atan2(math.tan(hfov * 0.5), aspect)

    fx = width / (2.0 * math.tan(hfov * 0.5))
    fy = height / (2.0 * math.tan(vfov * 0.5))

    cx = width * 0.5
    cy = height * 0.5

    camToWorld = BuildTransformationMatrix(position, lookAt)

    for y in range(0, height, 1):
        for x in range(0, width, 1):

            rawDepth = int(depthRaw[y, x])

            if rawDepth == 0 or rawDepth == 0xf81f:
                continue

            z = DecodeDepth(rawDepth, depthNear, depthFar)

            if z > maxDepth:
                continue

            nx = (x - cx) / fx
            ny = (y - cy) / fy

            wX = nx * z
            wY = ny * z

            point = (camToWorld @ np.array([wX, -wY, -z, 1.0]))[:3]

            index = len(points)

            vertexIndex[y, x] = index
            depths[y, x] = z

            points.append(point)
            colors.append(background[y, x])

    points = np.array(points, dtype=np.float64)
    colors = np.array(colors, dtype=np.uint8)
    faces = []

    if pointsOnly:
        return points, colors, faces

    maxDepthJump = max(depthSkip, z * 0.01)

    for y in range(height - 1):
        for x in range(width - 1):

            a = vertexIndex[y, x]
            b = vertexIndex[y, x + 1]
            c = vertexIndex[y + 1, x]
            d = vertexIndex[y + 1, x + 1]

            if a >= 0 and b >= 0 and d >= 0:

                za = depths[y, x]
                zb = depths[y, x + 1]
                zd = depths[y + 1, x + 1]

                if (
                    abs(za - zb) < maxDepthJump and
                    abs(zb - zd) < maxDepthJump and
                    abs(za - zd) < maxDepthJump
                ):
                    faces.append((a, d, b))

            if a >= 0 and c >= 0 and d >= 0:

                za = depths[y, x]
                zc = depths[y + 1, x]
                zd = depths[y + 1, x + 1]

                if (
                    abs(za - zc) < maxDepthJump and
                    abs(zc - zd) < maxDepthJump and
                    abs(za - zd) < maxDepthJump
                ):
                    faces.append((a, c, d))

    faces = np.array(faces, dtype=np.int32)

    return points, colors, faces

def main():

    parser = argparse.ArgumentParser()

    scriptDir = Path(__file__).resolve().parent

    parser.add_argument("--setups", required=True)
    parser.add_argument("--gamma", type=float, default=0.0, help="Gamma adjustment for vertex colors (0.0 to disable)")
    parser.add_argument("--maxDepth", type=float, default=50.0, help="Ignore depth values larger than this")
    parser.add_argument("--depthSkip", type=float, default=0.1, help="Value for deciding what should be triangulated")
    parser.add_argument("--pointsOnly", action="store_true", help="Skip meshing and output only a point cloud")

    args = parser.parse_args()

    names, positions, interests, fovs, nearClips, farClips = ReadSetups(Path(args.setups))

    for i in range(len(names)):

        print("Projecting setup:", names[i], "...")

        points, colors, faces = ProjectPoints(
            depthCsvPath = scriptDir / "CSV" / f"{names[i]}.csv",
            backgroundPath = scriptDir / "images" / f"{names[i]}.png",
            position = np.array(positions[i], dtype = np.float64),
            lookAt = np.array(interests[i], dtype = np.float64),
            fovDegrees = fovs[i],
            depthNear = nearClips[i],
            depthFar = farClips[i],
            gamma = args.gamma,
            maxDepth = args.maxDepth,
            depthSkip = args.depthSkip,
            pointsOnly = args.pointsOnly
        )

        outpath = scriptDir / "meshes" / f"{names[i]}.ply"

        print("points:", len(points))
        print("colors:", len(colors))
        print("faces:", len(faces))

        WriteBinaryPly(
            outpath,
            points,
            colors,
            None if args.pointsOnly else faces
        )

        print("Wrote", outpath,"\n")

    print("Finished")

if __name__ == "__main__":
    main()