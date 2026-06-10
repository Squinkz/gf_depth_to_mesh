from pathlib import Path
import argparse
import csv
import math
from title import Title
import numpy as np
from PIL import Image
from meshWriter import WriteBinaryPly, WriteOBJ


MODULE_NAME = "Grim Fandando Depth Map To Mesh"
MODULE_VERSION = [1, 2]
MODULE_AUTHOR = 'Dieter "squink" Stassen'


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

# Reads data from the camera setups
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

# Transform the points from camera space to world space
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

# Reads depth data
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

# Linearizes the depth data
def DecodeDepth(rawDepth, depthNear, depthFar):
    glDepth = 0xffff - ((rawDepth * 0x10000) // 100 // (0x10000 - rawDepth))
    glDepth = glDepth / 65535.0

    zNdc = glDepth * 2.0 - 1.0

    return (2.0 * depthNear * depthFar) / (
        depthFar + depthNear - zNdc * (depthFar - depthNear)
    )

# Projects the points into 3D
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

    vertexIndices = np.full((height, width), -1, dtype=np.int32)

    points = []
    colors = []
    uvs = []
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

            u = x / (width - 1)
            v = 1.0 - (y / (height - 1))

            index = len(points)

            vertexIndices[y, x] = index
            depths[y, x] = z

            points.append(point)
            colors.append(background[y, x])
            uvs.append((u, v))

    points = np.array(points, dtype=np.float64)
    colors = np.array(colors, dtype=np.uint8)
    uvs = np.array(uvs, dtype=np.float32)

    if pointsOnly:
        faces = np.empty((0, 3), dtype=np.int32)
    else:
        faces = BuildFaces(depthSkip, vertexIndices, depths)

    return points, colors, faces, uvs

# Triangulates and meshes the points
def BuildFaces(depthSkip, vertexIndices, depths):

    def CanMakeTriangle(z0, z1, z2, maxDepthJump):
        return (
            abs(z0 - z1) < maxDepthJump and
            abs(z1 - z2) < maxDepthJump and
            abs(z0 - z2) < maxDepthJump
        )

    faces = []
    height, width = vertexIndices.shape

    for y in range(height - 1):
        for x in range(width - 1):

            a = vertexIndices[y, x]
            b = vertexIndices[y, x + 1]
            c = vertexIndices[y + 1, x]
            d = vertexIndices[y + 1, x + 1]

            za = depths[y, x]
            zb = depths[y, x + 1]
            zc = depths[y + 1, x]
            zd = depths[y + 1, x + 1]

            validDepths = []

            if a >= 0:
                validDepths.append(za)
            if b >= 0:
                validDepths.append(zb)
            if c >= 0:
                validDepths.append(zc)
            if d >= 0:
                validDepths.append(zd)

            if len(validDepths) < 3:
                continue

            avgDepth = sum(validDepths) / len(validDepths)
            maxDepthJump = max(depthSkip, avgDepth * 0.01)

            if a >= 0 and b >= 0 and c >= 0 and d >= 0:
                diagAd = abs(za - zd)
                diagBc = abs(zb - zc)

                if diagAd <= diagBc:
                    if CanMakeTriangle(za, zb, zd, maxDepthJump):
                        faces.append((a, d, b))

                    if CanMakeTriangle(za, zc, zd, maxDepthJump):
                        faces.append((a, c, d))
                else:
                    if CanMakeTriangle(za, zc, zb, maxDepthJump):
                        faces.append((a, c, b))

                    if CanMakeTriangle(zb, zc, zd, maxDepthJump):
                        faces.append((b, c, d))

            else:
                if a >= 0 and b >= 0 and d >= 0:
                    if CanMakeTriangle(za, zb, zd, maxDepthJump):
                        faces.append((a, d, b))

                if a >= 0 and c >= 0 and d >= 0:
                    if CanMakeTriangle(za, zc, zd, maxDepthJump):
                        faces.append((a, c, d))

                if a >= 0 and b >= 0 and c >= 0:
                    if CanMakeTriangle(za, zc, zb, maxDepthJump):
                        faces.append((a, c, b))

                if b >= 0 and c >= 0 and d >= 0:
                    if CanMakeTriangle(zb, zc, zd, maxDepthJump):
                        faces.append((b, c, d))

    faces = np.array(faces, dtype=np.int32)

    return faces

def main():

    print(Title(MODULE_NAME, MODULE_VERSION, MODULE_AUTHOR))

    parser = argparse.ArgumentParser()

    scriptDir = Path(__file__).resolve().parent

    parser.add_argument("--setups", required=True)
    parser.add_argument("--gamma", type=float, default=0.0, help="Gamma adjustment for vertex colors (0.0 to disable)")
    parser.add_argument("--maxDepth", type=float, default=50.0, help="Ignore depth values larger than this")
    parser.add_argument("--depthSkip", type=float, default=0.1, help="Value for deciding what should be triangulated")
    parser.add_argument("--pointsOnly", action="store_true", help="Skip meshing and output only a point cloud")
    parser.add_argument(
        "--outFormat",
        choices=["PLY", "OBJ"],
        default="PLY",
        help="Output PLY with vertex colors or OBJ with UV data"
    )

    args = parser.parse_args()

    print("--gamma:\t", args.gamma)
    print("--maxDepth:\t", args.maxDepth)
    print("--depthSkip:\t", args.depthSkip)
    print("--pointsOnly:\t", args.pointsOnly)
    print("--outFormat:\t", args.outFormat)
    print("")

    names, positions, interests, fovs, nearClips, farClips = ReadSetups(Path(args.setups))

    for i in range(len(names)):

        print("Projecting setup:", names[i], "...")

        points, colors, faces, uvs = ProjectPoints(
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

        print("\tpoints:\t", len(points))
        print("\tfaces:\t", len(faces))

        if args.outFormat == "PLY":
            outpath = scriptDir / "meshes" / f"{names[i]}.ply"
            WriteBinaryPly(
                outpath,
                points,
                colors,
                None if args.pointsOnly else faces
            )
        else:
            outpath = scriptDir / "meshes" / f"{names[i]}.obj"
            WriteOBJ(
                outpath,
                points,
                uvs,
                None if args.pointsOnly else faces
            )

        print("Wrote", outpath,"\n")

    print("Finished")

if __name__ == "__main__":
    main()