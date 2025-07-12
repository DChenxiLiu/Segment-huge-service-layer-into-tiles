from arcgis.gis import GIS
from arcgis.raster import ImageryLayer
import os
import time
import requests

# --- CONFIGURATION ---
service_url = "https://sampleserver6.arcgisonline.com/arcgis/rest/services/NLCDLandCover2001/ImageServer"
output_dir = "tiles"
tile_size = 2000  # in meters (2km x 2km tiles)
# ---------------------

# Connect to ArcGIS Online (anonymous)
gis = GIS()

# Connect to the image service
try:
    img_layer = ImageryLayer(service_url, gis=gis)
    extent = img_layer.extent
    if not extent:
        raise ValueError("Could not retrieve extent from the image service. Check the service URL and your access.")
except Exception as e:
    print(f"Failed to connect to image service: {e}")
    exit(1)

xmin, ymin, xmax, ymax = extent['xmin'], extent['ymin'], extent['xmax'], extent['ymax']

# Create output directory
os.makedirs(output_dir, exist_ok=True)

# Calculate number of tiles in x and y direction
x_steps = int((xmax - xmin) // tile_size) + 1
y_steps = int((ymax - ymin) // tile_size) + 1

# Only extract the first 3x3 tiles as an example
max_tiles_x = 3
max_tiles_y = 3

for i in range(min(x_steps, max_tiles_x)):
    for j in range(min(y_steps, max_tiles_y)):
        x0 = xmin + i * tile_size
        x1 = min(x0 + tile_size, xmax)
        y0 = ymin + j * tile_size
        y1 = min(y0 + tile_size, ymax)
        bbox = {'xmin': x0, 'ymin': y0, 'xmax': x1, 'ymax': y1, 'spatialReference': extent['spatialReference']}
        out_path = os.path.join(output_dir, f"tile_{i}_{j}.tif")
        print(f"Exporting tile {i},{j} to {out_path} ...")
        try:
            result = img_layer.export_image(
                bbox=bbox, size=[1024, 1024],
                save_folder=output_dir, save_file=f"tile_{i}_{j}.tif", export_format="tiff"
            )
            href = result.get('href')
            if href:
                response = requests.get(href)
                if response.status_code == 200:
                    with open(out_path, 'wb') as f:
                        f.write(response.content)
                    print(f"Downloaded tile {i},{j} to {out_path}")
                else:
                    print(f"Failed to download tile {i},{j} from {href}")
            else:
                print(f"No href found for tile {i},{j}")
        except Exception as e:
            print(f"Failed to export tile {i},{j}: {e}")
        time.sleep(1)  # polite delay between requests

print("Tiling complete.")