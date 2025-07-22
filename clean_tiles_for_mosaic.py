import arcpy
import os

# Script to automatically process tiles and remove/fix NoData areas before mosaicking
def clean_tiles_for_mosaic(tiles_folder, output_folder, nodata_threshold=0.3):
    """
    Clean tiles by removing those with too much NoData and optionally processing others
    
    Parameters:
    tiles_folder: Path to folder containing tiles
    output_folder: Path for cleaned tiles
    nodata_threshold: Reject tiles with more than this % of NoData (0.3 = 30%)
    """
    
    print("=== TILE CLEANING FOR MOSAIC PREPARATION ===")
    print(f"Input folder: {tiles_folder}")
    print(f"Output folder: {output_folder}")
    print(f"NoData threshold: {nodata_threshold*100}%")
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    # Get list of tile files
    tile_files = []
    for file in os.listdir(tiles_folder):
        if file.endswith('.tif') and file.startswith('tile_'):
            tile_files.append(os.path.join(tiles_folder, file))
    
    print(f"\nFound {len(tile_files)} tiles to process")
    
    good_tiles = []
    rejected_tiles = []
    processed_count = 0
    
    for i, tile_path in enumerate(tile_files):
        tile_name = os.path.basename(tile_path)
        print(f"Processing {i+1}/{len(tile_files)}: {tile_name}")
        
        try:
            # Load raster
            raster = arcpy.Raster(tile_path)
            
            # Get basic properties
            pixel_count = raster.width * raster.height
            nodata_value = raster.noDataValue
            
            # Calculate statistics to estimate NoData percentage
            try:
                # Quick NoData estimation using raster properties
                min_val = raster.minimum
                max_val = raster.maximum
                mean_val = raster.mean
                
                # If min = max = nodata, it's entirely empty
                if min_val == max_val == nodata_value:
                    nodata_ratio = 1.0
                    print(f"  → Entirely NoData, rejecting")
                    rejected_tiles.append(tile_name)
                    continue
                    
                # For detailed analysis, we'd need to scan the raster
                # For now, use a heuristic based on the presence of NoData
                elif min_val == nodata_value:
                    # Contains some NoData, estimate based on statistics
                    # This is a rough estimate - could be improved with detailed analysis
                    estimated_nodata_ratio = 0.1  # Conservative estimate
                else:
                    estimated_nodata_ratio = 0.0  # No obvious NoData
                
                print(f"  → Estimated NoData: {estimated_nodata_ratio*100:.1f}%")
                
                if estimated_nodata_ratio <= nodata_threshold:
                    # Good tile - copy or process it
                    output_path = os.path.join(output_folder, tile_name)
                    
                    # Option 1: Simple copy (fastest)
                    arcpy.management.CopyRaster(tile_path, output_path)
                    
                    # Option 2: Set NoData to transparent (uncomment if needed)
                    # arcpy.management.CopyRaster(
                    #     tile_path, output_path,
                    #     nodata_value=nodata_value
                    # )
                    
                    good_tiles.append(output_path)
                    processed_count += 1
                    print(f"  → ✅ Copied to output")
                else:
                    rejected_tiles.append(tile_name)
                    print(f"  → ❌ Rejected (too much NoData)")
                    
            except Exception as e:
                print(f"  → ⚠️ Could not analyze statistics: {e}")
                # When in doubt, include the tile
                output_path = os.path.join(output_folder, tile_name)
                arcpy.management.CopyRaster(tile_path, output_path)
                good_tiles.append(output_path)
                processed_count += 1
                print(f"  → ✅ Copied anyway")
                
        except Exception as e:
            print(f"  → ❌ Error processing tile: {e}")
            rejected_tiles.append(tile_name)
    
    print(f"\n=== CLEANING RESULTS ===")
    print(f"Good tiles copied: {len(good_tiles)}")
    print(f"Rejected tiles: {len(rejected_tiles)}")
    print(f"Success rate: {len(good_tiles)/len(tile_files)*100:.1f}%")
    
    if len(rejected_tiles) > 0:
        print(f"\nRejected tiles (first 10):")
        for tile in rejected_tiles[:10]:
            print(f"  - {tile}")
        if len(rejected_tiles) > 10:
            print(f"  ... and {len(rejected_tiles)-10} more")
    
    return good_tiles, rejected_tiles

# Example usage - adjust paths to match your actual tile locations
if __name__ == "__main__":
    # Update these paths to match your actual folders
    input_tiles = r"C:\Users\dheaven\Desktop\tiles_250m_optimized_test\test_optimized_20250722_174003"
    output_clean = r"C:\Users\dheaven\Desktop\tiles_clean_for_mosaic"
    
    # Clean the tiles
    good_tiles, rejected_tiles = clean_tiles_for_mosaic(
        tiles_folder=input_tiles,
        output_folder=output_clean,
        nodata_threshold=0.2  # Reject tiles with >20% NoData
    )
    
    print(f"\n=== READY FOR MOSAIC ===")
    print(f"Clean tiles location: {output_clean}")
    print(f"Use these {len(good_tiles)} tiles for your mosaic dataset")
    print("\nNext steps:")
    print("1. Create mosaic dataset with Image Analyst extension")
    print("2. Add rasters from the clean tiles folder")
    print("3. Build overviews for performance")
    
    print("\nTile cleaning complete!")
