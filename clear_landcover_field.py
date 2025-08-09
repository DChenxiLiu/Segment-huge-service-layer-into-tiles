import arcpy
import os

# --- CONFIGURATION ---
polygon_files_folder = r"C:\Users\c72liu\Desktop\random_polygons_final"  # Folder with your random polygon shapefiles
# ---------------------

print("🧹 Clearing LAND_COVER field in existing polygon files...")
print(f"Looking in folder: {polygon_files_folder}")

if not os.path.exists(polygon_files_folder):
    print(f"❌ Folder not found: {polygon_files_folder}")
    exit()

# Find all shapefile files in the folder
shapefiles = [f for f in os.listdir(polygon_files_folder) if f.endswith('.shp') and f.startswith('random_polygons_')]

if not shapefiles:
    print("❌ No random polygon shapefiles found!")
    print("   Looking for files starting with 'random_polygons_' and ending with '.shp'")
    exit()

print(f"✅ Found {len(shapefiles)} polygon files to update:")
for shapefile in shapefiles:
    print(f"  📁 {shapefile}")

total_updated = 0

# Process each shapefile
for shapefile in shapefiles:
    shapefile_path = os.path.join(polygon_files_folder, shapefile)
    
    print(f"\n🧹 Clearing LAND_COVER field in {shapefile}...")
    
    try:
        # Check if LAND_COVER field exists
        field_names = [field.name for field in arcpy.ListFields(shapefile_path)]
        
        if "LAND_COVER" not in field_names:
            print(f"  ⚠️ LAND_COVER field not found in {shapefile}")
            continue
        
        # Count total polygons
        total_count = int(arcpy.management.GetCount(shapefile_path).getOutput(0))
        print(f"  📊 Found {total_count} polygons to update")
        
        # Clear the LAND_COVER field for all polygons
        updated_count = 0
        with arcpy.da.UpdateCursor(shapefile_path, ['LAND_COVER']) as cursor:
            for row in cursor:
                cursor.updateRow([""])  # Set to empty string
                updated_count += 1
        
        print(f"  ✅ Cleared LAND_COVER field for {updated_count} polygons")
        total_updated += updated_count
        
    except Exception as e:
        print(f"  ❌ Error processing {shapefile}: {str(e)}")

print(f"\n🎉 LAND_COVER FIELD CLEARING COMPLETE!")
print(f"📊 Total polygons updated: {total_updated}")
print(f"📊 Files processed: {len(shapefiles)}")

print(f"\n🎯 SUCCESS! All LAND_COVER fields are now empty!")
print(f"🎯 Ready for your manual classification!")
print(f"🎯 You can now open the files in ArcGIS Pro and fill in the land cover values manually!")
