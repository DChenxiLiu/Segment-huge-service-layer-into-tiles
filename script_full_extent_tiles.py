import arcpy
import os

project = arcpy.mp.ArcGISProject("CURRENT")
# layer_name = "Imagery_2024"   # We'll let user choose from available layers
output_dir = r"C:\Users\dheaven\Desktop\testingh_tiles_full"
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

# Calculate tile grid to cover the entire extent
xmin, ymin, xmax, ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax

# Calculate how many tiles needed to cover the entire extent
extent_width = xmax - xmin
extent_height = ymax - ymin
tiles_x = int(extent_width / tile_size) + 1  # Add 1 to ensure full coverage
tiles_y = int(extent_height / tile_size) + 1

total_tiles = tiles_x * tiles_y

print(f"Layer extent: {extent_width:.0f}m x {extent_height:.0f}m")
print(f"Creating {tiles_x} x {tiles_y} grid ({total_tiles} tiles total)")
print(f"Each tile: {tile_size}m x {tile_size}m")
print(f"Total coverage: {tiles_x*tile_size:.0f}m x {tiles_y*tile_size:.0f}m")

# Warning for large datasets
if total_tiles > 10000:
    print(f"\n⚠️  WARNING: This will create {total_tiles:,} tiles!")
    print("This could take a very long time and use significant disk space.")
    print("Consider reducing the extent or increasing tile size for testing.")
    response = input("Do you want to continue? (y/n): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        exit(0)

# Generate tile extents covering the entire area
tile_extents = []
for row in range(tiles_y):
    for col in range(tiles_x):
        # Calculate tile boundaries
        x0 = xmin + (col * tile_size)
        y0 = ymin + (row * tile_size)
        x1 = min(x0 + tile_size, xmax)  # Don't exceed layer extent
        y1 = min(y0 + tile_size, ymax)
        
        tile_extents.append((x0, y0, x1, y1, row + 1, col + 1))

print(f"Generated {len(tile_extents)} tile positions")

# Progress tracking
progress_interval = max(1, len(tile_extents) // 20)  # Show progress every 5%

for idx, (x0, y0, x1, y1, row, col) in enumerate(tile_extents):
    out_path = os.path.join(output_dir, f"tile_r{row:02d}_c{col:02d}.tif")
    
    # Show progress for large datasets
    if idx % progress_interval == 0 or idx == len(tile_extents) - 1:
        progress = (idx + 1) / len(tile_extents) * 100
        print(f"\nProgress: {progress:.1f}% ({idx+1}/{len(tile_extents)})")
    
    print(f"Exporting tile {idx+1}/{len(tile_extents)} (Row {row}, Col {col}) to {os.path.basename(out_path)} ...")
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

print("\nTile export complete!")

# Count successfully exported tiles
exported_tiles = []
for idx, (x0, y0, x1, y1, row, col) in enumerate(tile_extents):
    tile_path = os.path.join(output_dir, f"tile_r{row:02d}_c{col:02d}.tif")
    if os.path.exists(tile_path):
        exported_tiles.append(tile_path)

print("\n=== SUMMARY ===")
print(f"Tiles exported: {len(exported_tiles)}/{len(tile_extents)}")
print(f"Output directory: {output_dir}")
print("Files created:")
if len(exported_tiles) > 0:
    print(f"  - Individual tiles: tile_r01_c01.tif through tile_r{tiles_y:02d}_c{tiles_x:02d}.tif")
    print(f"  - Total coverage: {tiles_x*tile_size:.0f}m x {tiles_y*tile_size:.0f}m")
    print(f"  - Grid dimensions: {tiles_x} columns x {tiles_y} rows")
    
    # Estimate file size
    if len(exported_tiles) >= 4:
        # Use your observed ratio: 4 tiles = 13MB
        estimated_total_size = (len(exported_tiles) * 13) / 4  # MB
        if estimated_total_size > 1024:
            print(f"  - Estimated total size: {estimated_total_size/1024:.1f} GB")
        else:
            print(f"  - Estimated total size: {estimated_total_size:.0f} MB")
else:
    print("  - No tiles were successfully exported")
