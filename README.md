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

You will need Grimja Gui and LibLab library:

https://github.com/jlaw90/Grimja

You will also need a local copy of liblab repo in order to dump the depth buffers to CSV.

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

Use the Grimja GUI for this.

Right-click the `.zbm` file and choose **Extract**.

## 3. Converting Depth Maps to CSV

This step requires LibLab.

Place the Java file in the Grimja directory, then edit the `.bat` file and update the paths as needed.

Run the `.bat` file. It should produce a CSV file for the depth map.

Place the resulting CSV file in:

```text
csv/
```

## 4. Obtaining the Background Images

Use the Grimja GUI for this as well.

Export the `.bm` files using the PNG export option, don't rip the `.bm` files directly.

Place the exported PNG files in:

```text
images/
```

## Running the Script

Edit `run.bat` and change the path so that it points to your setup file.

Example:

```bat
python zbmToMesh.py --setups "C:\MyProject\setups.txt"
```

Save `run.bat`, then double-click it.

The generated `.PLY` meshes will be written to:

```text
meshes/
```
