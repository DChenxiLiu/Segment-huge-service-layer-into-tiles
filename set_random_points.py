# pip install rasterio geopandas

import rasterio
import numpy as np
import pandas as pd
from shapely.geometry import Point
import geopandas as gpd
import os

# --- CONFIGURATION ---
tiles_dir = r"C:\Users\c72liu\OneDrive - University of Waterloo\Projects\WR_tiles\local_tiles"  # Folder containing tiles
num_points = 200
# ---------------------

tile_files = [f for f in os.listdir(tiles_dir) if f.lower().endswith('.tif')]

for tile_file in tile_files:
    raster_path = os.path.join(tiles_dir, tile_file)
    output_shp = os.path.splitext(tile_file)[0] + "_points.shp"
    output_shp = os.path.join(tiles_dir, output_shp)
    with rasterio.open(raster_path) as src:
        width = src.width
        height = src.height
        transform = src.transform

        # Generate random row/col indices
        rows = np.random.randint(0, height, num_points)
        cols = np.random.randint(0, width, num_points)

        # Convert row/col to x/y coordinates
        xs, ys = rasterio.transform.xy(transform, rows, cols)
        points = [Point(x, y) for x, y in zip(xs, ys)]

        # Optionally, filter out points that fall on nodata
        if src.nodata is not None:
            values = [src.read(1)[row, col] for row, col in zip(rows, cols)]
            valid = [v != src.nodata for v in values]
            points = [pt for pt, v in zip(points, valid) if v]

        # Save as shapefile
        gdf = gpd.GeoDataFrame(geometry=points, crs=src.crs)
        gdf.to_file(output_shp)
        print(f"Saved {len(points)} random points as {output_shp}")