# Grim Fandango Depth Buffer to Mesh

This script reconstructs meshes from Grim Fandango depth buffers, background images, and camera setup data.

The output is a set of binary `.PLY` meshes with vertex colors.

## Requirements

You will need:

* Background images exported as PNG files
* Depth maps converted to CSV files
* Camera setup data from `.SET` files

## Folder Structure

```text
root/
│
├── setups.txt
│
├── images/
│   ├── camera0.png
│   ├── camera1.png
│   └── ...
│
├── csv/
│   ├── camera0.csv
│   ├── camera1.csv
│   └── ...
│
└── meshes/
```

The filenames in `images/` must match the filenames in `csv/`, and both must match the setup names in `setups.txt`.

For example:

```text
images/mo_winws.png
csv/mo_winws.csv
```

must correspond to:

```text
setup mo_winws
```

inside `setups.txt`.

## Obtaining the Required Files

You will need Grimja GUI and/or liblab library:

https://github.com/jlaw90/Grimja

You will also need a local copy of liblab repo in order to dump the depth buffers to CSV. If you use the attached script to dump the whole LAB file, you don't need Grimja GUI at all, just the liblab repo.

## 1. Obtaining Camera Setup Data

The camera setup data comes from `.SET` files extracted from Grim Fandango LAB files using Grimja GUI.

A `.SET` file may look something like this:

```text
section: colormaps
    numcolormaps 1
    colormap yr1_pal1.cmp

section: setups
    numsetups 7

    setup mo_ddtws
    background mo_0_ddtws.bm
    zbuffer mo_0_ddtws.zbm
    position 0.571882 2.461178 0.362781
    interest 1.089404 1.127796 0.217699
    roll 0.000000
    fov 75.178040
    nclip 0.010000
    fclip 3276.800049

    setup mo_winws
    background mo_1_winws.bm
    zbuffer mo_1_winws.zbm
    position 1.471700 0.051800 0.481300
    interest 0.715000 1.728400 0.221800
    roll 0.000000
    fov 75.178040
    nclip 0.010000
    fclip 3276.800049
```

Ignore everything before:

```text
section: setups
```

Only copy the camera entries for which you have depth buffers.

Your edited `setups.txt` should look something like this:

```text
setup mo_ddtws
background mo_0_ddtws.bm
zbuffer mo_0_ddtws.zbm
position 0.571882 2.461178 0.362781
interest 1.089404 1.127796 0.217699
roll 0.000000
fov 75.178040
nclip 0.010000
fclip 3276.800049

setup mo_winws
background mo_1_winws.bm
zbuffer mo_1_winws.zbm
position 1.471700 0.051800 0.481300
interest 0.715000 1.728400 0.221800
roll 0.000000
fov 75.178040
nclip 0.010000
fclip 3276.800049
```

The setup file can be named whatever you want, because you specify it as a command-line argument.

## 2. Obtaining the Depth Maps

Depth maps come from .zbm files.

You can either extract them manually with Grimja GUI, or dump them from the entire LAB file using the included Java helper script.

The Java helper script writes the extracted .zbm files and also converts them to .csv.

Place the resulting CSV files in:

csv/

## 3. Obtaining the Background Images

Background images come from .bm files.

You can export them manually from Grimja GUI as PNG files, or use the included Java helper script to dump them from the LAB file.

Place the exported PNG files in:

images/

## Running the Script

Basic usage:

python depthToMesh.py --setups "setups.txt"

The generated .PLY meshes will be written to:

meshes/

You can also edit run.bat and change the path so that it points to your setup file, then double-click it.

## Command Line Options

| Option | Default | Description |
| --- | --- | --- |
| `--setups`<br> | Required | Path to the setup file, relative or absolute. |
| `--gamma`<br> | `0.0` | Gamma adjustment for vertex colors. `0.0` disables gamma correction. A value of `1.27` is reasonably close to the in-game appearance at default brightness. |
| `--maxDepth`<br> | `50.0` | Ignores reconstructed depth values larger than this. Useful for removing distant geometry and background spikes. |
| `--depthSkip`<br> | `0.1` | Controls triangle generation across depth discontinuities. Lower values reject more triangles; higher values allow more bridging across gaps. |
| `--pointsOnly`<br> | `False` | Skip mesh generation and output a point cloud only. |                                                                                                           |

