import arcpy
import os
import time
from datetime import datetime

project = arcpy.mp.ArcGISProject("CURRENT")
# Configuration for SMALL TEST of optimized processing
output_dir = r"C:\Users\dheaven\Desktop\tiles_250m_optimized_test"
tile_size = 250  
spatial_ref = arcpy.SpatialReference(26917)

# Test batch settings - small for validation
max_test_tiles = 100  # Only process first 100 tiles from optimized area
batch_size = 25       # Smaller batches for testing
max_retries = 3   
sleep_between_batches = 5   # Shorter sleep for testing
log_interval = 25           # Log every 25 tiles

# Create timestamped output folder
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = os.path.join(output_dir, f"test_optimized_{timestamp}")
os.makedirs(output_dir, exist_ok=True)

# Logging setup
log_file = os.path.join(output_dir, "test_optimized_log.txt")
failed_tiles_file = os.path.join(output_dir, "failed_tiles.txt")

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# Create output folder
log_message("=== TEST OPTIMIZED PROCESSING: 100 TILES FROM IMAGERY-RICH AREAS ===")
log_message(f"Output directory: {output_dir}")
log_message(f"TEST MODE: Processing only {max_test_tiles} tiles from optimized extent")

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

# ENHANCED OPTIMIZATION: More precise focus on imagery area
# Based on your updated image, avoid bottom AND right edges where coverage is partial
xmin, ymin, xmax, ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax

# More aggressive cropping to avoid partial coverage areas
imagery_coverage_ratio_y = 0.85  # Focus on top 85% (more conservative)
imagery_coverage_ratio_x = 0.95  # Slightly crop right edge too

# Adjust both X and Y extents to focus on full-coverage areas
extent_height = ymax - ymin
extent_width = xmax - xmin

# Crop from bottom (Y direction)
imagery_ymin = ymin + (extent_height * (1 - imagery_coverage_ratio_y))
imagery_ymax = ymax

# Slightly crop from right (X direction) to avoid edge artifacts
imagery_xmin = xmin
imagery_xmax = xmax - (extent_width * (1 - imagery_coverage_ratio_x))

# Use the enhanced optimized extent
optimized_xmin = imagery_xmin
optimized_ymin = imagery_ymin
optimized_xmax = imagery_xmax  
optimized_ymax = imagery_ymax

log_message(f"Optimized extent (imagery focus): {optimized_xmin:.2f}, {optimized_ymin:.2f}, {optimized_xmax:.2f}, {optimized_ymax:.2f}")

# Calculate tile grid for optimized extent
extent_width = optimized_xmax - optimized_xmin
extent_height = optimized_ymax - optimized_ymin
tiles_x = int(extent_width / tile_size) + 1  
tiles_y = int(extent_height / tile_size) + 1

total_possible_tiles = tiles_x * tiles_y

log_message(f"Optimized area: {extent_width:.0f}m x {extent_height:.0f}m")
log_message(f"Full optimized grid would be: {tiles_x} x {tiles_y} ({total_possible_tiles:,} tiles total)")
log_message(f"TEST MODE: Only processing first {max_test_tiles} tiles from this optimized area")
log_message(f"Reduction vs original: ~{((extent.YMax - extent.YMin) * (extent.XMax - extent.XMin) - extent_width * extent_height) / ((extent.YMax - extent.YMin) * (extent.XMax - extent.XMin)) * 100:.0f}% fewer tiles")

# Generate tile extents for optimized area (but limit to test amount)
log_message("Generating optimized test tile grid...")
tile_extents = []
tile_count = 0

for row in range(tiles_y):
    if tile_count >= max_test_tiles:
        break
    for col in range(tiles_x):
        if tile_count >= max_test_tiles:
            break
            
        # Calculate tile boundaries
        x0 = optimized_xmin + (col * tile_size)
        y0 = optimized_ymin + (row * tile_size)
        x1 = min(x0 + tile_size, optimized_xmax)  
        y1 = min(y0 + tile_size, optimized_ymax)
        
        tile_extents.append((x0, y0, x1, y1, row + 1, col + 1))
        tile_count += 1

log_message(f"✓ Generated {len(tile_extents)} optimized test tile positions")

# Estimate test processing time
estimated_minutes = len(tile_extents) / 10  # Expect ~10 tiles per minute for data-rich areas
log_message(f"Estimated test time: {estimated_minutes:.1f} minutes")

log_message("Optimized test processing will begin in 3 seconds...")
time.sleep(3)

# Start batch processing
log_message("Starting OPTIMIZED TEST batch processing...")
start_time = time.time()
processed_count = 0
failed_count = 0
failed_tiles = []

for batch_start in range(0, len(tile_extents), batch_size):
    batch_end = min(batch_start + batch_size, len(tile_extents))
    batch_tiles = tile_extents[batch_start:batch_end]
    
    batch_num = (batch_start // batch_size) + 1
    total_batches = (len(tile_extents) + batch_size - 1) // batch_size
    
    log_message(f"--- TEST BATCH {batch_num}/{total_batches} ---")
    
    for idx, (x0, y0, x1, y1, row, col) in enumerate(batch_tiles):
        global_idx = batch_start + idx + 1
        out_path = os.path.join(output_dir, f"tile_r{row:04d}_c{col:04d}.tif")
        
        # Log progress
        if global_idx % log_interval == 0:
            elapsed = time.time() - start_time
            rate = global_idx / elapsed * 60  # tiles per minute
            remaining = (len(tile_extents) - global_idx) / rate if rate > 0 else 0
            progress = global_idx / len(tile_extents) * 100
            log_message(f"Progress: {progress:.1f}% ({global_idx}/{len(tile_extents)}) | "
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

log_message("\n=== OPTIMIZED TEST COMPLETE ===")
log_message(f"Test processing time: {total_time/60:.1f} minutes")
log_message(f"Successfully processed: {processed_count} tiles")
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
    log_message(f"Actual storage used: {actual_size_mb:.1f} MB for {tile_count} files")
    avg_tile_size = actual_size / tile_count / (1024*1024) if tile_count > 0 else 0
    log_message(f"Average tile size: {avg_tile_size:.2f} MB")

log_message(f"Test output directory: {output_dir}")
if failed_count > 0:
    log_message(f"Failed tiles list: {failed_tiles_file}")

# Extrapolate to full optimized dataset
if processed_count > 0:
    actual_rate = processed_count / (total_time / 3600)  # tiles per hour
    full_optimized_time_estimate = total_possible_tiles / actual_rate
    full_optimized_storage_estimate = (actual_size / processed_count * total_possible_tiles) / (1024**3)
    
    log_message("\n=== FULL OPTIMIZED DATASET PROJECTIONS ===")
    log_message(f"Actual processing rate: {actual_rate:.0f} tiles/hour")
    log_message(f"Full optimized dataset estimated time: {full_optimized_time_estimate:.1f} hours")
    log_message(f"Full optimized dataset estimated storage: {full_optimized_storage_estimate:.1f} GB")

# Compare with previous unoptimized test
log_message("\n=== OPTIMIZATION COMPARISON ===")
log_message("Previous unoptimized test results:")
log_message("  - Average tile size: 0.18 MB (many NoData tiles)")
log_message("  - Full dataset estimate: 75.3 hours, 7.6 GB")
log_message(f"Optimized test results:")
log_message(f"  - Average tile size: {avg_tile_size:.2f} MB (imagery-rich tiles)")
if processed_count > 0:
    log_message(f"  - Full optimized estimate: {full_optimized_time_estimate:.1f} hours, {full_optimized_storage_estimate:.1f} GB")

log_message("\n=== TEST RESULTS & RECOMMENDATIONS ===")
if processed_count >= len(tile_extents) * 0.95:  # 95% success rate
    if avg_tile_size > 0.5:  # Tiles are significantly larger than before
        log_message("✅ OPTIMIZATION SUCCESSFUL!")
        log_message("✅ Tiles contain more actual imagery data")
        log_message("✅ File sizes are more realistic for imagery content")
        log_message("✅ Ready to proceed with full optimized processing")
        log_message(f"✅ Recommended: Run optimized_tiles_script.py with test_mode=False")
    else:
        log_message("⚠️ TILES STILL SMALL - may still be in low-data areas")
        log_message("⚠️ Consider adjusting imagery_coverage_ratio or extent")
        log_message("⚠️ Visually inspect test tiles to verify imagery content")
else:
    log_message("⚠️ TEST SHOWS PROCESSING ISSUES")
    log_message("⚠️ High failure rate detected")
    log_message("⚠️ Review errors before proceeding")

log_message("\n=== NEXT STEPS ===")
log_message("1. Open ArcGIS Pro and visually inspect the test tiles")
log_message("2. Verify tiles contain good imagery (not mostly empty/water)")
log_message("3. If tiles look good, proceed with full optimized processing")
log_message("4. If tiles still seem empty, adjust imagery_coverage_ratio")

log_message("\nOptimized test complete!")
