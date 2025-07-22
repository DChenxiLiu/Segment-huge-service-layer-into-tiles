import arcpy
import os
import time
from datetime import datetime

project = arcpy.mp.ArcGISProject("CURRENT")
# Configuration for 150,000 tiles processing
output_dir = r"C:\Users\dheaven\Desktop\tiles_150k"
tile_size = 100  # 100m x 100m tiles
spatial_ref = arcpy.SpatialReference(26917)

# Large-scale processing settings
batch_size = 100  # Process 100 tiles per batch
max_retries = 3   # Retry failed tiles
sleep_between_batches = 15  # seconds rest between batches
log_interval = 500  # Log progress every 500 tiles

# Create timestamped output folder
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = os.path.join(output_dir, f"batch_{timestamp}")
os.makedirs(output_dir, exist_ok=True)

# Logging setup
log_file = os.path.join(output_dir, "processing_log.txt")
failed_tiles_file = os.path.join(output_dir, "failed_tiles.txt")

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# Create output folder
log_message("=== 150K TILES PROCESSING STARTED ===")
log_message(f"Output directory: {output_dir}")
log_message(f"Target: 150,000 tiles at {tile_size}m x {tile_size}m each")

# Get the active map
map_ = project.activeMap
if not map_:
    map_ = project.listMaps()[0]

log_message(f"Working with map: '{map_.name}'")
log_message("Scanning for imagery layers...")

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
    log_message(f"✓ Using layer: '{layer.name}'")
else:
    log_message("❌ No imagery layer found automatically.")
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

log_message(f"Layer extent: {extent.XMin:.2f}, {extent.YMin:.2f}, {extent.XMax:.2f}, {extent.YMax:.2f}")

# Calculate tile grid to cover the entire extent
xmin, ymin, xmax, ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax

# Calculate how many tiles needed to cover the entire extent
extent_width = xmax - xmin
extent_height = ymax - ymin
tiles_x = int(extent_width / tile_size) + 1  # Add 1 to ensure full coverage
tiles_y = int(extent_height / tile_size) + 1

total_tiles = tiles_x * tiles_y

log_message(f"Layer extent: {extent_width:.0f}m x {extent_height:.0f}m")
log_message(f"Creating {tiles_x} x {tiles_y} grid ({total_tiles:,} tiles total)")
log_message(f"Each tile: {tile_size}m x {tile_size}m")

# Estimate processing time and storage
estimated_hours = total_tiles / 1000  # Assume ~1000 tiles per hour
estimated_size_gb = (total_tiles * 3.25) / 1024  # 3.25MB per tile average

log_message(f"Estimated processing time: {estimated_hours:.1f} hours")
log_message(f"Estimated storage needed: {estimated_size_gb:.1f} GB")

# Confirm processing for large datasets
if total_tiles != 150000:
    log_message(f"⚠️  Note: Calculated {total_tiles:,} tiles, target was 150,000")
    if total_tiles > 200000:
        log_message("Consider adjusting tile size or extent to get closer to 150K tiles")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            log_message("Processing cancelled.")
            exit(0)

# Generate tile extents covering the entire area
log_message("Generating tile grid...")
tile_extents = []
for row in range(tiles_y):
    for col in range(tiles_x):
        # Calculate tile boundaries
        x0 = xmin + (col * tile_size)
        y0 = ymin + (row * tile_size)
        x1 = min(x0 + tile_size, xmax)  # Don't exceed layer extent
        y1 = min(y0 + tile_size, ymax)
        
        tile_extents.append((x0, y0, x1, y1, row + 1, col + 1))

log_message(f"✓ Generated {len(tile_extents):,} tile positions")

# Start batch processing
log_message("Starting batch processing...")
start_time = time.time()
processed_count = 0
failed_count = 0
failed_tiles = []

for batch_start in range(0, len(tile_extents), batch_size):
    batch_end = min(batch_start + batch_size, len(tile_extents))
    batch_tiles = tile_extents[batch_start:batch_end]
    
    batch_num = (batch_start // batch_size) + 1
    total_batches = (len(tile_extents) + batch_size - 1) // batch_size
    
    log_message(f"--- BATCH {batch_num:,}/{total_batches:,} ---")
    
    for idx, (x0, y0, x1, y1, row, col) in enumerate(batch_tiles):
        global_idx = batch_start + idx + 1
        out_path = os.path.join(output_dir, f"tile_r{row:04d}_c{col:04d}.tif")
        
        # Log progress
        if global_idx % log_interval == 0:
            elapsed = time.time() - start_time
            rate = global_idx / elapsed * 3600  # tiles per hour
            remaining = (len(tile_extents) - global_idx) / rate if rate > 0 else 0
            progress = global_idx / len(tile_extents) * 100
            log_message(f"Progress: {progress:.1f}% ({global_idx:,}/{len(tile_extents):,}) | "
                       f"Rate: {rate:.0f} tiles/hour | ETA: {remaining:.1f} hours")
        
        extent_str = f"{x0} {y0} {x1} {y1}"
        
        # Process with retries
        success = False
        for attempt in range(max_retries):
            try:
                arcpy.management.Clip(
                    in_raster=layer,
                    rectangle=extent_str,
                    out_raster=out_path,
                    nodata_value="-9999",
                    clipping_geometry="NONE",
                    maintain_clipping_extent="MAINTAIN_EXTENT"
                )
                processed_count += 1
                success = True
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)  # Brief pause before retry
                else:
                    failed_count += 1
                    failed_tiles.append(f"Tile {global_idx}: row {row}, col {col} - {str(e)[:100]}")
                    # Log to failed tiles file
                    with open(failed_tiles_file, "a", encoding="utf-8") as f:
                        f.write(f"Tile {global_idx}: row {row:04d}, col {col:04d}, extent {extent_str}\n")
    
    # Rest between batches
    if batch_num < total_batches:
        time.sleep(sleep_between_batches)

# Final processing summary
end_time = time.time()
total_time = end_time - start_time

log_message("\n=== 150K TILES PROCESSING COMPLETE ===")
log_message(f"Total processing time: {total_time/3600:.1f} hours")
log_message(f"Successfully processed: {processed_count:,} tiles")
log_message(f"Failed tiles: {failed_count:,}")
log_message(f"Success rate: {(processed_count/len(tile_extents)*100):.1f}%")

# Calculate actual storage used
actual_size = 0
tile_count = 0
for root, dirs, files in os.walk(output_dir):
    for file in files:
        if file.endswith('.tif'):
            file_path = os.path.join(root, file)
            actual_size += os.path.getsize(file_path)
            tile_count += 1

if actual_size > 0:
    actual_size_gb = actual_size / (1024**3)
    log_message(f"Actual storage used: {actual_size_gb:.1f} GB for {tile_count:,} files")
    avg_tile_size = actual_size / tile_count / (1024*1024) if tile_count > 0 else 0
    log_message(f"Average tile size: {avg_tile_size:.2f} MB")

log_message(f"Output directory: {output_dir}")
if failed_count > 0:
    log_message(f"Failed tiles list: {failed_tiles_file}")

log_message("\n=== NEXT STEPS ===")
log_message("1. Review failed tiles and reprocess if needed")
log_message("2. Create mosaic dataset from the tiles:")
log_message("   - Use 'Create Mosaic Dataset' tool")
log_message("   - Add tiles using 'Add Rasters to Mosaic Dataset'")
log_message("   - Build overviews for better performance")
log_message("3. Consider creating tile cache for web services")

log_message("Processing complete!")
