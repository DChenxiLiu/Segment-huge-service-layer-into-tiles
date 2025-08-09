import arcpy
import os

# --- CONFIGURATION ---
imagery_layer_name = "Imagery_2024"  # Your imagery layer name in ArcGIS Pro
output_folder = r"C:\Users\c72liu\Desktop\irregular_sections"  # Where to save truly irregular shapefiles
# ---------------------

# Create output directory
os.makedirs(output_folder, exist_ok=True)

print("🎯 Creating TRULY IRREGULAR sections from your imagery!")
print("This approach will create sections that follow the actual data boundaries...")

# Get the current map and imagery layer
print("Getting imagery layer from current map...")
aprx = arcpy.mp.ArcGISProject("CURRENT")
map_ = aprx.listMaps()[0]
imagery_layer = map_.listLayers(imagery_layer_name)[0]

print(f"Found imagery layer: {imagery_layer.name}")

# Get the imagery properties
desc = arcpy.Describe(imagery_layer)
extent = desc.extent
spatial_ref = desc.spatialReference

# Calculate center point
center_x = (extent.XMin + extent.XMax) / 2
center_y = (extent.YMin + extent.YMax) / 2

print(f"Imagery extent: {extent.XMin:.0f}, {extent.YMin:.0f}, {extent.XMax:.0f}, {extent.YMax:.0f}")
print(f"Center point: x={center_x:.0f}, y={center_y:.0f}")

# Create temporary small rasters for each quadrant
temp_rasters = []
temp_polygons = []

try:
    # Define quadrant extents
    quadrants = [
        ("topleft", extent.XMin, center_y, center_x, extent.YMax),
        ("topright", center_x, center_y, extent.XMax, extent.YMax),
        ("bottomleft", extent.XMin, extent.YMin, center_x, center_y),
        ("bottomright", center_x, extent.YMin, extent.XMax, center_y)
    ]
    
    for i, (quad_name, xmin, ymin, xmax, ymax) in enumerate(quadrants):
        print(f"\n🔥 Creating IRREGULAR {quad_name} section...")
        
        # Create extent for this quadrant
        quad_extent = f"{xmin} {ymin} {xmax} {ymax}"
        
        # Temporary file names
        temp_small = f"temp_small_{i}"
        temp_poly = f"temp_poly_{i}"
        
        temp_rasters.append(temp_small)
        temp_polygons.append(temp_poly)
        
        try:
            print(f"  📊 Exporting {quad_name} quadrant with safe parameters...")
            
            # Calculate appropriate cell size to stay within limits
            quad_width = xmax - xmin
            quad_height = ymax - ymin
            
            # Calculate cell size to stay well within the 4100x15000 limits
            max_pixels = 1500  # Use 1500 to be very safe
            cell_size_x = quad_width / max_pixels
            cell_size_y = quad_height / max_pixels
            cell_size = max(cell_size_x, cell_size_y)
            
            print(f"    Quadrant size: {quad_width:.0f} x {quad_height:.0f} meters")
            print(f"    Using cell size: {cell_size:.2f} meters")
            print(f"    Estimated pixels: {quad_width/cell_size:.0f} x {quad_height/cell_size:.0f}")
            
            # Use Make Raster Layer with extent and then Copy
            temp_layer = f"temp_layer_{i}"
            
            print(f"  🎯 Creating raster layer for {quad_name}...")
            arcpy.management.MakeRasterLayer(
                in_raster=imagery_layer.dataSource,
                out_rasterlayer=temp_layer,
                where_clause="",
                envelope=f"{xmin} {ymin} {xmax} {ymax}"
            )
            
            print(f"  � Exporting with controlled cell size...")
            # Export with controlled cell size
            with arcpy.EnvManager(cellSize=cell_size):
                arcpy.management.CopyRaster(
                    in_raster=temp_layer,
                    out_rasterdataset=temp_small,
                    config_keyword="",
                    background_value="",
                    nodata_value="",
                    onebit_to_eightbit="NONE",
                    colormap_to_RGB="NONE",
                    pixel_type="",
                    scale_pixel_value="NONE",
                    RGB_to_Colormap="NONE",
                    format="TIFF"
                )
            
            # Clean up the temporary layer
            arcpy.management.Delete(temp_layer)
            
            print(f"  🗺️ Converting to irregular polygon...")
            # Convert to polygon - this will give us the irregular shape!
            arcpy.conversion.RasterToPolygon(
                in_raster=temp_small,
                out_polygon_features=temp_poly,
                simplify="NO_SIMPLIFY",
                raster_field="Value",
                create_multipart_features="SINGLE_OUTER_PART"
            )
            
            print(f"  ✨ Processing irregular polygons...")
            # Read and union all polygons to get the boundary
            irregular_polygons = []
            with arcpy.da.SearchCursor(temp_poly, ["SHAPE@"]) as cursor:
                for row in cursor:
                    if row[0] and row[0].area > 0:
                        irregular_polygons.append(row[0])
            
            if irregular_polygons:
                # Union all polygons to get the complete irregular shape
                if len(irregular_polygons) == 1:
                    final_shape = irregular_polygons[0]
                else:
                    final_shape = irregular_polygons[0]
                    for poly in irregular_polygons[1:]:
                        final_shape = final_shape.union(poly)
                
                # Create output shapefile
                output_name = f"irregular_{quad_name}_section.shp"
                output_path = os.path.join(output_folder, output_name)
                
                print(f"  💾 Saving irregular shapefile: {output_name}")
                arcpy.management.CreateFeatureclass(
                    out_path=output_folder,
                    out_name=output_name,
                    geometry_type="POLYGON",
                    spatial_reference=spatial_ref
                )
                
                # Add fields
                arcpy.management.AddField(output_path, "SECTION", "TEXT", field_length=20)
                arcpy.management.AddField(output_path, "AREA_M2", "DOUBLE")
                arcpy.management.AddField(output_path, "AREA_KM2", "DOUBLE")
                
                # Calculate areas
                area_m2 = final_shape.area
                area_km2 = area_m2 / 1000000
                
                # Insert the irregular geometry
                with arcpy.da.InsertCursor(output_path, ['SHAPE@', 'SECTION', 'AREA_M2', 'AREA_KM2']) as cursor:
                    cursor.insertRow([final_shape, quad_name, area_m2, area_km2])
                
                print(f"  ✅ SUCCESS! Created IRREGULAR {quad_name} section")
                print(f"     Area: {area_km2:.2f} km² ({area_m2:.0f} m²)")
                print(f"     File: {output_path}")
            else:
                print(f"  ⚠️ No data found in {quad_name} quadrant")
                
        except Exception as quad_error:
            print(f"  ❌ Failed to process {quad_name}: {quad_error}")

finally:
    # Clean up temporary files
    print("\n🧹 Cleaning up temporary files...")
    for temp_file in temp_rasters + temp_polygons:
        if arcpy.Exists(temp_file):
            try:
                arcpy.management.Delete(temp_file)
                print(f"  Deleted: {temp_file}")
            except:
                print(f"  Could not delete: {temp_file}")

print(f"\n🎉 IRREGULAR SECTIONS COMPLETE!")
print(f"Your irregular-shaped sections are saved in: {output_folder}")

# List final results
print(f"\n📁 Irregular section files created:")
if os.path.exists(output_folder):
    files = [f for f in os.listdir(output_folder) if f.endswith('.shp')]
    if files:
        for file in files:
            file_path = os.path.join(output_folder, file)
            try:
                with arcpy.da.SearchCursor(file_path, ["AREA_KM2"]) as cursor:
                    for row in cursor:
                        area_km2 = row[0]
                        print(f"  🗺️ {file} ({area_km2:.2f} km²)")
                        break
            except:
                print(f"  🗺️ {file}")
    else:
        print("  No files created")
else:
    print("  Output folder not found")

print("\n🎯 These sections follow the ACTUAL IRREGULAR boundaries of your imagery data!")
print("🎯 Add them to your map to see the true data coverage areas!")
