import arcpy
import os

project = arcpy.mp.ArcGISProject("CURRENT")
# layer_name = "Imagery_2024"   # We'll let user choose from available layers
output_dir = r"C:\Users\dheaven\Desktop\testingh_tiles"
tile_size = 100  # Drastically reduced to 100 meters to stay within server limits
spatial_ref = arcpy.SpatialReference(26917)  # Change to match your projection

# Create output folder
os.makedirs(output_dir, exist_ok=True)

# Get the active map
map_ = project.activeMap
if not map_:
    map_ = project.listMaps()[0]

print(f"Working with map: '{map_.name}'")
print("\nAll available layers:")

# List all layers with their index for easy selection
all_layers = map_.listLayers()
for i, lyr in enumerate(all_layers):
    layer_type = type(lyr).__name__
    print(f"  [{i}] {lyr.name} (Type: {layer_type})")
    
    # Show additional info for web layers
    if hasattr(lyr, 'isWebLayer'):
        print(f"      Web Layer: {lyr.isWebLayer}")
    if hasattr(lyr, 'connectionProperties'):
        try:
            conn_props = lyr.connectionProperties
            if 'url' in conn_props:
                print(f"      URL: {conn_props['url'][:80]}...")
        except:
            pass

# Let user choose by index or try to find imagery layer automatically
imagery_layer = None
for lyr in all_layers:
    # Look for common imagery layer patterns including your specific server
    keywords = ['imagery', 'image', 'aerial', 'satellite', '2024', 'imageserver', 'regionofwaterloo', 'treecanopy']
    if any(keyword in lyr.name.lower() for keyword in keywords):
        print(f"\nFound potential imagery layer: '{lyr.name}'")
        imagery_layer = lyr
        break

# Also check for layers with specific connection properties
if not imagery_layer:
    for lyr in all_layers:
        if hasattr(lyr, 'connectionProperties'):
            try:
                conn_props = lyr.connectionProperties
                if 'url' in conn_props:
                    url = conn_props['url'].lower()
                    if 'imageserver' in url or 'regionofwaterloo' in url:
                        print(f"\nFound imagery layer by connection URL: '{lyr.name}'")
                        print(f"URL: {conn_props['url']}")
                        imagery_layer = lyr
                        break
            except:
                pass

if imagery_layer:
    layer = imagery_layer
    print(f"Using layer: '{layer.name}'")
else:
    print(f"\nNo imagery layer found automatically.")
    print("Available layers to choose from:")
    for i, lyr in enumerate(all_layers):
        print(f"  [{i}] {lyr.name}")
    print("\nTo use a specific layer, add this line after the layer listing:")
    print("layer = all_layers[X]  # Replace X with the index number")
    print("For example: layer = all_layers[0]")
    exit(1)

# Get extent of the layer
desc = arcpy.Describe(layer)
extent = desc.extent

print(f"Layer extent: {extent.XMin}, {extent.YMin}, {extent.XMax}, {extent.YMax}")

# For image services, let's check the pixel size to calculate safe tile dimensions
try:
    # Get raster properties to understand pixel size
    cell_size_x = desc.meanCellWidth if hasattr(desc, 'meanCellWidth') else 1.0
    cell_size_y = desc.meanCellHeight if hasattr(desc, 'meanCellHeight') else 1.0
    print(f"Estimated cell size: {cell_size_x} x {cell_size_y} meters")
    
    # Calculate how many pixels our tile will be
    pixels_x = tile_size / cell_size_x
    pixels_y = tile_size / cell_size_y
    print(f"Tile size in pixels: {pixels_x:.0f} x {pixels_y:.0f}")
    
    # Be very conservative with server limits - use much smaller values
    max_safe_pixels = 1000  # Very conservative limit
    if pixels_x > max_safe_pixels or pixels_y > max_safe_pixels:
        # Adjust tile size to be very small
        tile_size = max_safe_pixels * min(cell_size_x, cell_size_y)
        pixels_x = tile_size / cell_size_x
        pixels_y = tile_size / cell_size_y
        print(f"Adjusted tile size to {tile_size:.0f} meters ({pixels_x:.0f}x{pixels_y:.0f} pixels)")
        
except Exception as e:
    print(f"Could not determine cell size: {e}")
    print("Using very small default tile size for safety")
    tile_size = 50  # Even smaller fallback

print(f"Final tile size: {tile_size} meters")

# Calculate tile grid (8x8 tiles for larger coverage)
xmin, ymin, xmax, ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax
center_x = (xmin + xmax) / 2
center_y = (ymin + ymax) / 2

# Create 8x8 grid of tiles
grid_size = 8  # 8x8 = 64 tiles total
half_grid = grid_size // 2

print(f"Creating {grid_size}x{grid_size} grid ({grid_size*grid_size} tiles total)")
print(f"Each tile: {tile_size}m x {tile_size}m")
print(f"Total coverage: {grid_size*tile_size}m x {grid_size*tile_size}m")

offsets = []
for row in range(grid_size):
    for col in range(grid_size):
        # Calculate offset from center
        dx = (col - half_grid + 0.5) * tile_size
        dy = (row - half_grid + 0.5) * tile_size
        offsets.append((dx, dy))

print(f"Generated {len(offsets)} tile positions")

for idx, (dx, dy) in enumerate(offsets):
    x0 = center_x + dx
    x1 = x0 + tile_size
    y0 = center_y + dy
    y1 = y0 + tile_size
    
    # Calculate row and column for better naming
    row = idx // grid_size + 1
    col = idx % grid_size + 1
    out_path = os.path.join(output_dir, f"tile_r{row:02d}_c{col:02d}.tif")
    
    print(f"Exporting tile {idx+1}/{len(offsets)} (Row {row}, Col {col}) to {os.path.basename(out_path)} ...")
    print(f"  Extent: {x0:.2f}, {y0:.2f}, {x1:.2f}, {y1:.2f}")
    
    # Create extent string
    extent_str = f"{x0} {y0} {x1} {y1}"

    try:
        # Clip raster using extent
        arcpy.management.Clip(
            in_raster=layer,
            rectangle=extent_str,
            out_raster=out_path,
            nodata_value="-9999",
            clipping_geometry="NONE",
            maintain_clipping_extent="MAINTAIN_EXTENT"
        )
        print(f"  ✓ Successfully exported tile {idx+1}")
    except Exception as e:
        print(f"  ✗ Error exporting tile {idx+1}: {e}")
        print(f"  Try reducing tile_size further (current: {tile_size} meters)")
        continue

print(" Export complete.")

# === STITCHING TILES TOGETHER ===
print("\nStitching tiles together...")

# Collect all successfully exported tiles
exported_tiles = []
for idx in range(len(offsets)):
    row = idx // grid_size + 1
    col = idx % grid_size + 1
    tile_path = os.path.join(output_dir, f"tile_r{row:02d}_c{col:02d}.tif")
    if os.path.exists(tile_path):
        exported_tiles.append(tile_path)
        print(f"Found tile: tile_r{row:02d}_c{col:02d}.tif")

if len(exported_tiles) > 1:
    # Create mosaic output path
    mosaic_path = os.path.join(output_dir, "stitched_mosaic.tif")
    
    try:
        print(f"Creating mosaic from {len(exported_tiles)} tiles...")
        
        # Use arcpy.management.MosaicToNewRaster to stitch tiles
        arcpy.management.MosaicToNewRaster(
            input_rasters=exported_tiles,
            output_location=output_dir,
            raster_dataset_name_with_extension="stitched_mosaic.tif",
            coordinate_system_for_the_raster=spatial_ref,
            pixel_type="8_BIT_UNSIGNED",  # Adjust based on your imagery
            cellsize="",  # Use original cellsize
            number_of_bands="3",  # RGB imagery, adjust if needed
            mosaic_method="FIRST",  # Use first tile's values for overlaps
            mosaic_colormap_mode="FIRST"
        )
        
        print(f"✓ Successfully created mosaic: {mosaic_path}")
        print(f"  Combined {len(exported_tiles)} tiles into single image")
        
        # Optional: Create a larger mosaic with more spacing
        larger_mosaic_path = os.path.join(output_dir, "analysis_ready_mosaic.tif")
        
        # Also create a copy with better compression for analysis
        arcpy.management.CopyRaster(
            in_raster=mosaic_path,
            out_rasterdataset=larger_mosaic_path,
            format="TIFF",
            compression="LZW",
            nodata_value="-9999"
        )
        
        print(f"✓ Created analysis-ready copy: analysis_ready_mosaic.tif")
        
    except Exception as e:
        print(f"✗ Error creating mosaic: {e}")
        print("You can manually mosaic the tiles using ArcGIS Pro:")
        print("1. Data Management Tools > Raster > Raster Dataset > Mosaic to New Raster")
        print("2. Input the tile files and create a single output raster")

elif len(exported_tiles) == 1:
    print("Only one tile exported - copying as analysis-ready file...")
    analysis_path = os.path.join(output_dir, "analysis_ready_single.tif")
    arcpy.management.CopyRaster(
        in_raster=exported_tiles[0],
        out_rasterdataset=analysis_path,
        format="TIFF",
        compression="LZW"
    )
    print(f"✓ Created analysis-ready file: analysis_ready_single.tif")

else:
    print("No tiles were successfully exported to stitch together.")

print("\n=== SUMMARY ===")
print(f"Tiles exported: {len(exported_tiles)}")
print(f"Output directory: {output_dir}")
if len(exported_tiles) > 1:
    print("Files created:")
    print(f"  - Individual tiles: tile_r01_c01.tif through tile_r{grid_size:02d}_c{grid_size:02d}.tif")
    print("  - Stitched mosaic: stitched_mosaic.tif")
    print("  - Analysis ready: analysis_ready_mosaic.tif")
elif len(exported_tiles) == 1:
    print("Files created:")
    print("  - Single tile: tile_r01_c01.tif")
    print("  - Analysis ready: analysis_ready_single.tif")