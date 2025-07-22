import arcpy
import os

# Test mosaic creation with your existing 16 tiles
project = arcpy.mp.ArcGISProject("CURRENT")

# Configuration - using your existing test tiles
tiles_folder = r"C:\Users\dheaven\Desktop\testing_tiles"  # Your 4x4 test tiles folder
output_gdb = r"C:\Users\dheaven\Desktop\test_mosaic.gdb"  # Output geodatabase
mosaic_name = "Test_Imagery_Mosaic"
spatial_ref = arcpy.SpatialReference(26917)

print("=== TESTING MOSAIC CREATION ===")
print(f"Using tiles from: {tiles_folder}")
print(f"Output geodatabase: {output_gdb}")

# Step 1: Check if test tiles exist
tile_files = []
if os.path.exists(tiles_folder):
    for file in os.listdir(tiles_folder):
        if file.endswith('.tif') and file.startswith('tile_'):
            tile_files.append(os.path.join(tiles_folder, file))

if len(tile_files) == 0:
    print("❌ No test tiles found!")
    print("Please run your script_16tiles first to create test tiles.")
    exit(1)

print(f"✓ Found {len(tile_files)} test tiles")
for tile in tile_files[:5]:  # Show first 5
    print(f"  - {os.path.basename(tile)}")
if len(tile_files) > 5:
    print(f"  ... and {len(tile_files) - 5} more")

# Step 2: Create geodatabase if it doesn't exist
try:
    if not arcpy.Exists(output_gdb):
        print("Creating test geodatabase...")
        arcpy.management.CreateFileGDB(
            out_folder_path=os.path.dirname(output_gdb),
            out_name=os.path.basename(output_gdb)
        )
        print("✓ Geodatabase created")
    else:
        print("✓ Geodatabase already exists")
except Exception as e:
    print(f"❌ Error creating geodatabase: {e}")
    exit(1)

# Step 3: Create mosaic dataset
try:
    print("Creating mosaic dataset...")
    mosaic_path = os.path.join(output_gdb, mosaic_name)
    
    # Delete if already exists
    if arcpy.Exists(mosaic_path):
        arcpy.management.Delete(mosaic_path)
        print("  - Deleted existing mosaic")
    
    arcpy.management.CreateMosaicDataset(
        in_workspace=output_gdb,
        in_mosaicdataset_name=mosaic_name,  # Fixed: removed underscore
        coordinate_system=spatial_ref
    )
    print("✓ Mosaic dataset created successfully")
    
except Exception as e:
    print(f"❌ Error creating mosaic dataset: {e}")
    print("This might indicate you need additional licensing.")
    exit(1)

# Step 4: Add rasters to mosaic
try:
    print(f"Adding {len(tile_files)} tiles to mosaic...")
    arcpy.management.AddRastersToMosaicDataset(
        in_mosaic_dataset=mosaic_path,
        raster_type="Raster Dataset",
        input_path=tiles_folder,
        update_cellsize_ranges="UPDATE_CELL_SIZES",
        update_boundary="UPDATE_BOUNDARY",
        update_overviews="NO_OVERVIEWS"
    )
    print("✓ Tiles added to mosaic successfully")
    
except Exception as e:
    print(f"❌ Error adding rasters to mosaic: {e}")
    print("This might indicate you need additional licensing.")
    exit(1)

# Step 5: Build overviews (optional test)
try:
    print("Building overviews...")
    arcpy.management.BuildOverviews(
        in_mosaic_dataset=mosaic_path
    )
    print("✓ Overviews built successfully")
    
except Exception as e:
    print(f"⚠️ Warning: Could not build overviews: {e}")
    print("Overviews are optional - mosaic still functional")

# Step 6: Get mosaic information
try:
    print("\n=== MOSAIC INFORMATION ===")
    desc = arcpy.Describe(mosaic_path)
    print(f"Mosaic name: {desc.baseName}")
    print(f"Spatial reference: {desc.spatialReference.name}")
    print(f"Extent: {desc.extent.XMin:.0f}, {desc.extent.YMin:.0f}, {desc.extent.XMax:.0f}, {desc.extent.YMax:.0f}")
    
    # Count rasters in mosaic
    with arcpy.da.SearchCursor(mosaic_path, ["OBJECTID"]) as cursor:
        raster_count = sum(1 for row in cursor)
    print(f"Number of rasters in mosaic: {raster_count}")
    
except Exception as e:
    print(f"⚠️ Could not get mosaic information: {e}")

print("\n=== TEST RESULTS ===")
print("✅ SUCCESS: Mosaic creation works with your standard ArcGIS Pro license!")
print("✅ You can create mosaics from your tiles without additional licensing.")
print(f"\nTest mosaic created at: {mosaic_path}")
print("\n=== NEXT STEPS ===")
print("1. Open ArcGIS Pro and add the test mosaic to your map")
print("2. Verify it displays all tiles seamlessly")
print("3. If everything looks good, proceed with your full 43,000 tile processing")
print("4. NO ADDITIONAL LICENSE PURCHASE NEEDED! 🎉")

print("\nTest complete!")
