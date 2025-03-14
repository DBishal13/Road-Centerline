# Centerline Calculation Notebook

This notebook, `Notebooks/centerline.ipynb`, is designed to process a shapefile containing road polygons, densify the polygons by adding points along their edges, and then calculate the centerline of these polygons. The resulting centerlines are saved to a new shapefile. The notebook is based on the `pygeoops.centerline` module: [pygeoops.centerline documentation](https://pygeoops.readthedocs.io/en/stable/api/pygeoops.centerline.html)

## Prerequisites

Ensure you have the following Python packages installed:
- `numpy`
- `geopandas`
- `shapely`
- `pygeoops`

You can install these packages using pip:
```sh
pip install numpy geopandas shapely pygeoops
