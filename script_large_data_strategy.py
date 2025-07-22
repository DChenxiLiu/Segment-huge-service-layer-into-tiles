import arcpy
import os
import time
from datetime import datetime

# Configuration for large data processing (1TB+)
project = arcpy.mp.ArcGISProject("CURRENT")
base_output_dir = r"C:\Users\dheaven\Desktop\large_tiles"
tile_size = 500  # Larger tiles for efficiency - 500m x 500m
spatial_ref = arcpy.SpatialReference(26917)

# Batch processing settings
batch_size = 50  # Process 50 tiles at a time
max_retries = 3  # Retry failed tiles
sleep_between_batches = 30  # seconds - give server a break

# Create timestamped output folder
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = os.path.join(base_output_dir, f"tiles_{timestamp}")
os.makedirs(output_dir, exist_ok=True)

# Error tracking
error_log_path = os.path.join(output_dir, "processing_log.txt")
failed_tiles_path = os.path.join(output_dir, "failed_tiles.txt")

def log_message(message):
    """Log messages to both console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(error_log_path, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def estimate_processing_time(total_tiles, tiles_per_hour=100):
    """Estimate total processing time"""
    hours = total_tiles / tiles_per_hour
    if hours < 24:
        return f"{hours:.1f} hours"
    else:
        days = hours / 24
        return f"{days:.1f} days"

# Get the active map and layer
map_ = project.activeMap
if not map_:
    map_ = project.listMaps()[0]

log_message("=== LARGE DATA TILING PROCESS STARTED ===")
log_message(f"Output directory: {output_dir}")

# Auto-detect imagery layer
imagery_layer = None
all_layers = map_.listLayers()

for lyr in all_layers:
    keywords = ['imagery', 'image', 'aerial', 'satellite', '2024', 'imageserver', 'treecanopy']
    if any(keyword in lyr.name.lower() for keyword in keywords):
        imagery_layer = lyr
        break

if not imagery_layer:
    log_message("ERROR: No imagery layer found automatically.")
    exit(1)

layer = imagery_layer
log_message(f"Using layer: '{layer.name}'")

# Get extent and calculate tiles
desc = arcpy.Describe(layer)
extent = desc.extent
xmin, ymin, xmax, ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax

extent_width = xmax - xmin
extent_height = ymax - ymin
tiles_x = int(extent_width / tile_size) + 1
tiles_y = int(extent_height / tile_size) + 1
total_tiles = tiles_x * tiles_y

log_message(f"Layer extent: {extent_width:.0f}m x {extent_height:.0f}m")
log_message(f"Creating {tiles_x} x {tiles_y} grid ({total_tiles:,} tiles total)")
log_message(f"Each tile: {tile_size}m x {tile_size}m")
log_message(f"Estimated processing time: {estimate_processing_time(total_tiles)}")

# Calculate estimated size
estimated_size_gb = (total_tiles * 13 / 4) / 1024  # Based on your 4 tiles = 13MB
log_message(f"Estimated total size: {estimated_size_gb:.1f} GB")

if total_tiles > 50000:
    log_message(f"⚠️  WARNING: {total_tiles:,} tiles is very large!")
    log_message("Consider processing in geographic regions or increasing tile size.")
    response = input("Continue with full processing? (y/n): ")
    if response.lower() != 'y':
        log_message("Processing cancelled by user.")
        exit(0)

# Generate all tile extents
log_message("Generating tile positions...")
tile_extents = []
for row in range(tiles_y):
    for col in range(tiles_x):
        x0 = xmin + (col * tile_size)
        y0 = ymin + (row * tile_size)
        x1 = min(x0 + tile_size, xmax)
        y1 = min(y0 + tile_size, ymax)
        tile_extents.append((x0, y0, x1, y1, row + 1, col + 1))

log_message(f"Generated {len(tile_extents):,} tile positions")

# Process tiles in batches
failed_tiles = []
processed_count = 0
start_time = time.time()

for batch_start in range(0, len(tile_extents), batch_size):
    batch_end = min(batch_start + batch_size, len(tile_extents))
    batch_tiles = tile_extents[batch_start:batch_end]
    
    batch_num = (batch_start // batch_size) + 1
    total_batches = (len(tile_extents) + batch_size - 1) // batch_size
    
    log_message(f"\n--- BATCH {batch_num}/{total_batches} ---")
    log_message(f"Processing tiles {batch_start + 1} to {batch_end}")
    
    for idx, (x0, y0, x1, y1, row, col) in enumerate(batch_tiles):
        global_idx = batch_start + idx
        out_path = os.path.join(output_dir, f"tile_r{row:03d}_c{col:03d}.tif")
        
        # Progress within batch
        if idx % 10 == 0 or idx == len(batch_tiles) - 1:
            overall_progress = (global_idx + 1) / len(tile_extents) * 100
            log_message(f"Overall progress: {overall_progress:.1f}% ({global_idx + 1:,}/{len(tile_extents):,})")
        
        extent_str = f"{x0} {y0} {x1} {y1}"
        
        # Retry logic
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
                    log_message(f"  Retry {attempt + 1}/{max_retries} for tile {global_idx + 1}: {str(e)[:100]}")
                    time.sleep(5)  # Wait before retry
                else:
                    log_message(f"  FAILED tile {global_idx + 1} after {max_retries} attempts: {str(e)[:100]}")
                    failed_tiles.append((global_idx + 1, row, col, str(e)))
        
        if not success:
            # Log failed tile details
            with open(failed_tiles_path, "a", encoding="utf-8") as f:
                f.write(f"Tile {global_idx + 1}: row {row}, col {col}, extent {extent_str}\n")
    
    # Rest between batches to avoid overwhelming the server
    if batch_num < total_batches:
        log_message(f"Batch {batch_num} complete. Resting {sleep_between_batches} seconds...")
        time.sleep(sleep_between_batches)

# Final summary
end_time = time.time()
processing_time = end_time - start_time
log_message("\n=== PROCESSING COMPLETE ===")
log_message(f"Total processing time: {processing_time/3600:.1f} hours")
log_message(f"Tiles processed successfully: {processed_count:,}/{len(tile_extents):,}")
log_message(f"Failed tiles: {len(failed_tiles):,}")

if failed_tiles:
    log_message(f"Failed tiles logged to: {failed_tiles_path}")
    log_message("You can reprocess failed tiles later by modifying the extent list.")

# Calculate actual size
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
    log_message(f"Actual output size: {actual_size_gb:.1f} GB ({tile_count:,} files)")

log_message(f"Processing log saved to: {error_log_path}")
log_message("=== END OF PROCESSING ===")
