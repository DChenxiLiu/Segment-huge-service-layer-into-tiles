import arcpy
import os

# --- CONFIGURATION ---
imagery_layer_name = "Imagery_2024"  # Your imagery layer name in ArcGIS Pro
output_folder = r"C:\Users\c72liu\Desktop\clipped_shapefiles"  # Where to save irregular-shaped shapefiles
# ---------------------

# Create output directory
os.makedirs(output_folder, exist_ok=True)

# Get the current map and imagery layer
print("Getting imagery layer from current map...")
aprx = arcpy.mp.ArcGISProject("CURRENT")
map_ = aprx.listMaps()[0]
imagery_layer = map_.listLayers(imagery_layer_name)[0]

print(f"Found imagery layer: {imagery_layer.name}")

# Get the actual imagery footprint (not just extent)
print("Extracting actual imagery footprint...")
desc = arcpy.Describe(imagery_layer)

# Extract the actual irregular footprint of the imagery
print("Getting imagery boundary using layer properties...")
try:
    # Method 1: Try to get the layer's visible extent/boundary
    print("  Attempting to get layer boundary from properties...")
    
    # Get the layer's definition and properties
    layer_def = imagery_layer.getDefinition()
    
    # Try to get footprint from layer if available
    if hasattr(layer_def, 'footprint') and layer_def.footprint:
        print("  Found layer footprint property...")
        # Convert footprint to geometry if available
        footprint_geom = layer_def.footprint
        imagery_boundary = arcpy.Polygon(footprint_geom, desc.spatialReference)
        print(f"  ✅ Successfully got imagery boundary from layer footprint")
    else:
        # Method 2: Try to create a downsampled version for boundary detection
        print("  Attempting boundary detection with downsampled raster...")
        temp_small_raster = "temp_small_raster"
        temp_footprint = "temp_footprint"
        
        try:
            # Create a very small version of the raster for boundary detection
            extent = desc.extent
            cell_size = max((extent.XMax - extent.XMin) / 100, (extent.YMax - extent.YMin) / 100)
            
            print(f"    Creating downsampled raster with cell size: {cell_size:.2f}")
            arcpy.management.Resample(
                in_raster=imagery_layer.dataSource,
                out_raster=temp_small_raster,
                cell_size=cell_size,
                resampling_type="NEAREST"
            )
            
            # Convert the small raster to polygon
            print("    Converting small raster to polygon...")
            arcpy.RasterToPolygon_conversion(
                in_raster=temp_small_raster,
                out_polygon_features=temp_footprint,
                simplify="SIMPLIFY",
                raster_field="Value"
            )
            
            # Read the footprint geometry
            footprint_polygons = []
            with arcpy.da.SearchCursor(temp_footprint, ["SHAPE@"]) as cursor:
                for row in cursor:
                    if row[0] and row[0].area > 0:
                        footprint_polygons.append(row[0])
            
            if footprint_polygons:
                # Union all polygons to get the complete footprint
                if len(footprint_polygons) == 1:
                    imagery_boundary = footprint_polygons[0]
                else:
                    imagery_boundary = footprint_polygons[0]
                    for poly in footprint_polygons[1:]:
                        imagery_boundary = imagery_boundary.union(poly)
                print(f"  ✅ Successfully extracted irregular boundary from downsampled raster")
            else:
                raise Exception("No polygons found in downsampled raster")
                
        except Exception as downsample_error:
            print(f"    Downsampling failed: {downsample_error}")
            raise Exception("Downsampling approach failed")
            
        finally:
            # Clean up temporary files
            for temp_file in [temp_small_raster, temp_footprint]:
                if arcpy.Exists(temp_file):
                    arcpy.management.Delete(temp_file)
    
    print(f"  ✅ Imagery boundary area: {imagery_boundary.area:.2f}")
        
except Exception as e:
    print(f"  ⚠️ Could not get irregular boundary ({e}), using extent boundary...")
    # Fallback: Use basic extent
    extent = desc.extent
    imagery_boundary_array = arcpy.Array([
        arcpy.Point(extent.XMin, extent.YMin),
        arcpy.Point(extent.XMin, extent.YMax),
        arcpy.Point(extent.XMax, extent.YMax),
        arcpy.Point(extent.XMax, extent.YMin),
        arcpy.Point(extent.XMin, extent.YMin)
    ])
    imagery_boundary = arcpy.Polygon(imagery_boundary_array, desc.spatialReference)
    print(f"  Using extent boundary with area: {imagery_boundary.area:.2f}")

# Get the extent for center point calculation
extent = imagery_boundary.extent
center_x = (extent.XMin + extent.XMax) / 2
center_y = (extent.YMin + extent.YMax) / 2

print(f"Imagery center point: x={center_x:.2f}, y={center_y:.2f}")
print(f"Creating 4 irregular-shaped sections based on center point...")

# Create 4 clipping rectangles based on center point
quadrant_info = [
    ("topleft", extent.XMin, center_y, center_x, extent.YMax),
    ("topright", center_x, center_y, extent.XMax, extent.YMax),
    ("bottomleft", extent.XMin, extent.YMin, center_x, center_y),
    ("bottomright", center_x, extent.YMin, extent.XMax, center_y)
]

# Create each irregular-shaped section
for quadrant_name, x_min, y_min, x_max, y_max in quadrant_info:
    print(f"\nCreating {quadrant_name} irregular section...")
    
    # Create rectangular clipping polygon for this quadrant
    quadrant_array = arcpy.Array([
        arcpy.Point(x_min, y_min),
        arcpy.Point(x_min, y_max),
        arcpy.Point(x_max, y_max),
        arcpy.Point(x_max, y_min),
        arcpy.Point(x_min, y_min)
    ])
    quadrant_polygon = arcpy.Polygon(quadrant_array, desc.spatialReference)
    
    # Intersect the irregular imagery boundary with this quadrant
    print(f"  Intersecting irregular boundary with {quadrant_name} quadrant...")
    intersected_geometry = imagery_boundary.intersect(quadrant_polygon, 4)  # 4 = geometry intersection
    
    if intersected_geometry and intersected_geometry.area > 0:
        # Create output shapefile for this irregular section
        output_name = f"imagery_{quadrant_name}_irregular.shp"
        output_path = os.path.join(output_folder, output_name)
        
        print(f"  Creating irregular shapefile: {output_name}...")
        arcpy.management.CreateFeatureclass(
            out_path=output_folder,
            out_name=output_name,
            geometry_type="POLYGON",
            spatial_reference=desc.spatialReference
        )
        
        # Add fields to identify the section
        arcpy.management.AddField(output_path, "SECTION", "TEXT", field_length=20)
        arcpy.management.AddField(output_path, "AREA_M2", "DOUBLE")
        arcpy.management.AddField(output_path, "AREA_KM2", "DOUBLE")
        
        # Insert the irregular intersected geometry
        area_m2 = intersected_geometry.area
        area_km2 = area_m2 / 1000000
        
        with arcpy.da.InsertCursor(output_path, ['SHAPE@', 'SECTION', 'AREA_M2', 'AREA_KM2']) as cursor:
            cursor.insertRow([intersected_geometry, quadrant_name, area_m2, area_km2])
        
        print(f"✅ Successfully created irregular {quadrant_name} shapefile: {output_path}")
        print(f"   Area: {area_km2:.2f} km² ({area_m2:.2f} m²)")
    else:
        print(f"⚠️ No imagery found in {quadrant_name} quadrant")

print(f"\n✅ Irregular shapefile processing complete!")
print(f"Irregular imagery shapefiles saved to: {output_folder}")

# List all output files
print(f"\nIrregular shaped files created:")
if os.path.exists(output_folder):
    files = [f for f in os.listdir(output_folder) if f.endswith('.shp') and 'irregular' in f]
    for file in files:
        file_path = os.path.join(output_folder, file)
        # Get area from the shapefile
        try:
            with arcpy.da.SearchCursor(file_path, ["AREA_KM2"]) as cursor:
                for row in cursor:
                    area_km2 = row[0]
                    print(f"  - {file} ({area_km2:.2f} km²)")
                    break
        except:
            print(f"  - {file}")
else:
    print("  No output folder found")

print("\n🎯 You now have 4 irregular-shaped shapefiles that follow your imagery boundaries!")
