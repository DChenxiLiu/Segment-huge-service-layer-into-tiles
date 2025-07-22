import arcpy
import os
from PIL import Image
import numpy as np

# Script to analyze tile quality and investigate the small file sizes
test_tiles_dir = r"C:\Users\dheaven\Desktop\tiles_250m_test\test_batch_20250722_171402"

print("=== TILE QUALITY ANALYSIS ===")
print(f"Analyzing tiles in: {test_tiles_dir}")

if not os.path.exists(test_tiles_dir):
    print("❌ Test tiles directory not found!")
    print("Please run test_batch_tiles.py first.")
    exit(1)

# Get list of tile files
tile_files = []
for file in os.listdir(test_tiles_dir):
    if file.endswith('.tif') and file.startswith('tile_'):
        tile_files.append(os.path.join(test_tiles_dir, file))

if len(tile_files) == 0:
    print("❌ No tile files found!")
    exit(1)

print(f"Found {len(tile_files)} tiles to analyze")

# Analyze several tiles
sample_tiles = tile_files[:5]  # Analyze first 5 tiles

for i, tile_path in enumerate(sample_tiles):
    print(f"\n--- ANALYZING TILE {i+1}: {os.path.basename(tile_path)} ---")
    
    try:
        # Get basic file info
        file_size = os.path.getsize(tile_path) / (1024*1024)  # MB
        print(f"File size: {file_size:.2f} MB")
        
        # Use ArcPy to get raster properties
        desc = arcpy.Describe(tile_path)
        print(f"Format: {desc.format}")
        print(f"Compression: {desc.compressionType if hasattr(desc, 'compressionType') else 'Unknown'}")
        print(f"Pixel type: {desc.pixelType}")
        print(f"Band count: {desc.bandCount}")
        print(f"Width x Height: {desc.width} x {desc.height} pixels")
        print(f"Cell size: {desc.meanCellWidth} x {desc.meanCellHeight}")
        
        # Calculate expected size
        expected_pixels = desc.width * desc.height
        expected_size_uncompressed = expected_pixels * desc.bandCount * 3 / (1024*1024)  # Assuming 3 bytes per band
        compression_ratio = expected_size_uncompressed / file_size if file_size > 0 else 0
        
        print(f"Expected pixels: {expected_pixels:,}")
        print(f"Expected uncompressed size: {expected_size_uncompressed:.1f} MB")
        print(f"Compression ratio: {compression_ratio:.1f}:1")
        
        # Check for NoData values using ArcPy
        try:
            raster = arcpy.Raster(tile_path)
            
            # Get raster statistics
            print(f"NoData value: {raster.noDataValue}")
            
            # Try to get basic statistics
            print("Getting statistics...")
            mean = raster.mean
            std = raster.standardDeviation
            minimum = raster.minimum
            maximum = raster.maximum
            
            print(f"Statistics - Min: {minimum}, Max: {maximum}, Mean: {mean:.2f}, Std: {std:.2f}")
            
            # Check if mostly NoData
            if minimum == maximum == raster.noDataValue:
                print("⚠️ WARNING: Tile appears to be entirely NoData!")
            elif minimum == raster.noDataValue:
                print("ℹ️ Tile contains some NoData values")
            else:
                print("✅ Tile contains valid imagery data")
                
        except Exception as e:
            print(f"⚠️ Could not analyze raster statistics: {e}")
            
    except Exception as e:
        print(f"❌ Error analyzing tile: {e}")

# Overall analysis
print(f"\n=== OVERALL ANALYSIS ===")
total_size = sum(os.path.getsize(f) for f in tile_files) / (1024*1024)
avg_size = total_size / len(tile_files)
print(f"Total size of {len(tile_files)} tiles: {total_size:.1f} MB")
print(f"Average tile size: {avg_size:.2f} MB")

# Size comparison with expectations
print(f"\n=== SIZE ANALYSIS ===")
expected_tile_size_rgb = (250/1.0) * (250/1.0) * 3 / (1024*1024)  # 250m at 1m resolution, 3 bands, MB
print(f"Expected size per tile (RGB, uncompressed): {expected_tile_size_rgb:.1f} MB")
print(f"Actual average size: {avg_size:.2f} MB")
print(f"Compression factor: {expected_tile_size_rgb/avg_size:.1f}:1")

if avg_size < expected_tile_size_rgb * 0.01:  # Less than 1% of expected
    print("🚨 ALERT: Tiles are extremely small - likely mostly NoData or heavily compressed")
elif avg_size < expected_tile_size_rgb * 0.1:  # Less than 10% of expected
    print("⚠️ WARNING: Tiles are much smaller than expected - check for data quality issues")
else:
    print("✅ Tile sizes appear reasonable")

print(f"\n=== RECOMMENDATIONS ===")
print("1. Open one of the test tiles in ArcGIS Pro to visually inspect quality")
print("2. Check if tiles show actual imagery or just NoData/background")
print("3. If tiles are mostly empty, consider:")
print("   - Using a smaller area with known imagery coverage")
print("   - Checking if your extent covers areas with actual data")
print("   - Adjusting tile size or location")
print("4. Check compression settings - ensure you're getting full quality")

print(f"\n=== NEXT STEPS ===")
print("If tiles contain good imagery data:")
print("  → Proceed with full processing")
print("If tiles are mostly NoData:")
print("  → Adjust processing area to focus on data-rich regions")
print("  → Consider using imagery extent rather than full layer extent")

print("\nAnalysis complete!")
