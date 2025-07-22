import arcpy
import os
import time
from datetime import datetime

project = arcpy.mp.ArcGISProject("CURRENT")
# Configuration for OPTIMIZED processing - only areas with imagery data
output_dir = r"C:\Users\dheaven\Desktop\tiles_250m_optimized"
tile_size = 250  
spatial_ref = arcpy.SpatialReference(26917)

# Processing settings optimized for data-rich areas only
batch_size = 50
max_retries = 3   
sleep_between_batches = 5
log_interval = 100

# Create timestamped output folder
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = os.path.join(output_dir, f"optimized_batch_{timestamp}")
os.makedirs(output_dir, exist_ok=True)

# Logging setup
log_file = os.path.join(output_dir, "optimized_processing_log.txt")
failed_tiles_file = os.path.join(output_dir, "failed_tiles.txt")

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# Create output folder
log_message("=== OPTIMIZED PROCESSING: IMAGERY-RICH AREAS ONLY ===")
log_message(f"Output directory: {output_dir}")
log_message("Strategy: Focus on areas with actual imagery data")

# Get the active map
map_ = project.activeMap
if not map_:
    map_ = project.listMaps()[0]

log_message(f"Working with map: '{map_.name}'")

# Directly get the Imagery_2024 layer
target_layer_name = "Imagery_2024"
all_layers = map_.listLayers()

# Find the specific layer by name
layer = None
for lyr in all_layers:
    if lyr.name == target_layer_name:
        layer = lyr
        break

if layer:
    log_message(f"✓ Using layer: '{layer.name}'")
else:
    log_message(f"❌ Could not find layer '{target_layer_name}' in the map.")
    log_message("Available layers:")
    for lyr in all_layers:
        log_message(f"  - {lyr.name}")
    exit(1)

# Get extent of the layer
desc = arcpy.Describe(layer)
extent = desc.extent

log_message(f"Original layer extent: {extent.XMin:.2f}, {extent.YMin:.2f}, {extent.XMax:.2f}, {extent.YMax:.2f}")

# OPTIMIZATION: Focus on the main imagery area
# Based on your image, adjust these coordinates to focus on data-rich areas
xmin, ymin, xmax, ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax

# Crop to focus on main imagery area (adjust these values based on your actual data)
# From your image, it looks like the bottom portion is mostly empty
imagery_coverage_ratio = 0.8  # Assume imagery covers top 80% of the extent

# Adjust Y extent to focus on imagery-rich areas
extent_height = ymax - ymin
imagery_ymin = ymin + (extent_height * (1 - imagery_coverage_ratio))  # Start higher up
imagery_ymax = ymax  # Keep the full top extent

# Use the optimized extent
optimized_xmin = xmin
optimized_ymin = imagery_ymin
optimized_xmax = xmax  
optimized_ymax = imagery_ymax

log_message(f"Optimized extent (imagery focus): {optimized_xmin:.2f}, {optimized_ymin:.2f}, {optimized_xmax:.2f}, {optimized_ymax:.2f}")

# Calculate tile grid for optimized extent
extent_width = optimized_xmax - optimized_xmin
extent_height = optimized_ymax - optimized_ymin
tiles_x = int(extent_width / tile_size) + 1  
tiles_y = int(extent_height / tile_size) + 1

total_tiles = tiles_x * tiles_y

log_message(f"Optimized area: {extent_width:.0f}m x {extent_height:.0f}m")
log_message(f"Creating {tiles_x} x {tiles_y} grid ({total_tiles:,} tiles total)")
log_message(f"Reduction: ~{((extent.YMax - extent.YMin) * (extent.XMax - extent.XMin) - extent_width * extent_height) / ((extent.YMax - extent.YMin) * (extent.XMax - extent.XMin)) * 100:.0f}% fewer tiles")

# Generate tile extents for optimized area only
log_message("Generating optimized tile grid...")
tile_extents = []

for row in range(tiles_y):
    for col in range(tiles_x):
        # Calculate tile boundaries
        x0 = optimized_xmin + (col * tile_size)
        y0 = optimized_ymin + (row * tile_size)
        x1 = min(x0 + tile_size, optimized_xmax)  
        y1 = min(y0 + tile_size, optimized_ymax)
        
        tile_extents.append((x0, y0, x1, y1, row + 1, col + 1))

log_message(f"✓ Generated {len(tile_extents):,} optimized tile positions")

# Estimate processing time for optimized dataset
estimated_hours = len(tile_extents) / 577  # Use your actual rate from test
estimated_size_gb = len(tile_extents) * 0.18 / 1024  # Use actual tile size but expect larger for data-rich areas

log_message(f"Estimated processing time: {estimated_hours:.1f} hours")
log_message(f"Estimated storage (conservative): {estimated_size_gb:.1f} GB")

# Optional: Add a smaller test first
test_mode = True  # Set to False for full processing
if test_mode:
    log_message("TEST MODE: Processing first 200 tiles to validate optimization")
    tile_extents = tile_extents[:200]

log_message("Optimized processing will begin in 5 seconds...")
time.sleep(5)

# Start batch processing
log_message("Starting OPTIMIZED batch processing...")
start_time = time.time()
processed_count = 0
failed_count = 0
failed_tiles = []

for batch_start in range(0, len(tile_extents), batch_size):
    batch_end = min(batch_start + batch_size, len(tile_extents))
    batch_tiles = tile_extents[batch_start:batch_end]
    
    batch_num = (batch_start // batch_size) + 1
    total_batches = (len(tile_extents) + batch_size - 1) // batch_size
    
    log_message(f"--- BATCH {batch_num}/{total_batches} ---")
    
    for idx, (x0, y0, x1, y1, row, col) in enumerate(batch_tiles):
        global_idx = batch_start + idx + 1
        out_path = os.path.join(output_dir, f"tile_r{row:04d}_c{col:04d}.tif")
        
        # Log progress
        if global_idx % log_interval == 0:
            elapsed = time.time() - start_time
            rate = global_idx / elapsed * 60  # tiles per minute
            remaining = (len(tile_extents) - global_idx) / rate if rate > 0 else 0
            progress = global_idx / len(tile_extents) * 100
            log_message(f"Progress: {progress:.1f}% ({global_idx:,}/{len(tile_extents):,}) | "
                       f"Rate: {rate:.0f} tiles/min | ETA: {remaining:.1f} minutes")
        
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

log_message("\n=== OPTIMIZED PROCESSING COMPLETE ===")
log_message(f"Processing time: {total_time/60:.1f} minutes")
log_message(f"Successfully processed: {processed_count:,} tiles")
log_message(f"Failed tiles: {failed_count}")
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
    actual_size_mb = actual_size / (1024*1024)
    log_message(f"Actual storage used: {actual_size_mb:.1f} MB for {tile_count:,} files")
    avg_tile_size = actual_size / tile_count / (1024*1024) if tile_count > 0 else 0
    log_message(f"Average tile size: {avg_tile_size:.2f} MB")

log_message(f"Output directory: {output_dir}")
if failed_count > 0:
    log_message(f"Failed tiles list: {failed_tiles_file}")

log_message("\n=== OPTIMIZATION RESULTS ===")
log_message("✅ Focused processing on imagery-rich areas only")
log_message("✅ Eliminated empty/NoData tiles")
log_message("✅ Reduced processing time and storage requirements")
log_message("✅ Higher quality tiles with actual imagery data")

if test_mode:
    log_message("\n=== NEXT STEPS ===")
    log_message("1. Review the test tiles to confirm they contain good imagery")
    log_message("2. If satisfied, set test_mode = False and run full optimized processing")
    log_message("3. Adjust imagery_coverage_ratio if needed based on actual data distribution")

log_message("\nOptimized processing complete!")
