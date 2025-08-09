import arcpy
import os

# --- CONFIGURATION ---
layer_name = "Imagery_2024"  # Update with your exact layer name if different
output_dir = r"C:\Users\c72liu\Desktop\mask_shapefiles"
# ---------------------

# Create output directory
os.makedirs(output_dir, exist_ok=True)

# Get the current map and layer
print("Getting layer from current map...")
aprx = arcpy.mp.ArcGISProject("CURRENT")
map_ = aprx.listMaps()[0]
layer = map_.listLayers(layer_name)[0]

# Get extent from the layer
desc = arcpy.Describe(layer)
extent = desc.extent
spatial_ref = desc.spatialReference
print(f"Layer extent retrieved: {extent}")

# For large imagery services, we'll try to get the actual footprint instead of just extent
print("Getting actual imagery footprint...")

# Get extent for coordinate calculations
xmin, ymin, xmax, ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax
center_x = (xmin + xmax) / 2
center_y = (ymin + ymax) / 2

print(f"Extent: xmin={xmin}, ymin={ymin}, xmax={xmax}, ymax={ymax}")
print(f"Center: x={center_x}, y={center_y}")

# Try to get the actual footprint of the imagery (where there's data)
temp_footprint = "temp_footprint"
try:
    # Method 1: Try to get footprint from raster properties
    if hasattr(layer, 'dataSource'):
        print("  Attempting to extract raster footprint...")
        arcpy.management.RasterToPolygon(
            in_raster=layer.dataSource,
            out_polygon_features=temp_footprint,
            simplify="NO_SIMPLIFY",
            raster_field="Value",
            create_multipart_features="SINGLE_OUTER_PART",
            max_vertices_per_feature=None
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
                main_boundary = footprint_polygons[0]
            else:
                main_boundary = footprint_polygons[0]
                for poly in footprint_polygons[1:]:
                    main_boundary = main_boundary.union(poly)
            print(f"  ✅ Successfully extracted imagery footprint")
        else:
            raise Exception("No valid footprint polygons found")
            
    else:
        raise Exception("Cannot access raster data source")
        
except Exception as e:
    print(f"  ⚠️ Could not extract raster footprint ({e}), using extent boundary...")
    # Fallback: Create boundary from extent
    main_boundary_coords = [
        [xmin, ymin], [xmin, ymax], [xmax, ymax], [xmax, ymin], [xmin, ymin]
    ]
    # Create the main boundary polygon from coordinates
    boundary_array = arcpy.Array([arcpy.Point(x, y) for x, y in main_boundary_coords])
    main_boundary = arcpy.Polygon(boundary_array, spatial_ref)

finally:
    # Clean up temporary files
    if arcpy.Exists(temp_footprint):
        arcpy.management.Delete(temp_footprint)

print(f"Main boundary area: {main_boundary.area}")

# Define the 4 quadrants with their shapefile names
quadrants = [
    ("TopLeft", "mask_topleft.shp", xmin, center_y, center_x, ymax),
    ("TopRight", "mask_topright.shp", center_x, center_y, xmax, ymax),
    ("BottomLeft", "mask_bottomleft.shp", xmin, ymin, center_x, center_y),
    ("BottomRight", "mask_bottomright.shp", center_x, ymin, xmax, center_y)
]

print("Creating boundary-aligned shapefiles for each quadrant...")

# Create a separate shapefile for each quadrant, clipped to imagery boundary
for quadrant_name, shapefile_name, x_min, y_min, x_max, y_max in quadrants:
    print(f"Creating {quadrant_name} shapefile: {shapefile_name}")
    
    # Create rectangular quadrant polygon
    quadrant_array = arcpy.Array([
        arcpy.Point(x_min, y_min),
        arcpy.Point(x_min, y_max),
        arcpy.Point(x_max, y_max),
        arcpy.Point(x_max, y_min),
        arcpy.Point(x_min, y_min)
    ])
    quadrant_polygon = arcpy.Polygon(quadrant_array, spatial_ref)
    
    # Intersect the quadrant with the main boundary to get only the imagery area
    clipped_geometry = main_boundary.intersect(quadrant_polygon, 4)  # 4 = geometry intersection
    
    if clipped_geometry and clipped_geometry.area > 0:
        # Create output shapefile for this quadrant
        output_shapefile = os.path.join(output_dir, shapefile_name)
        arcpy.management.CreateFeatureclass(
            out_path=output_dir,
            out_name=shapefile_name,
            geometry_type="POLYGON",
            spatial_reference=spatial_ref
        )
        
        # Add a field to identify the quadrant
        arcpy.management.AddField(output_shapefile, "QUADRANT", "TEXT", field_length=20)
        
        # Insert the clipped polygon into the shapefile
        with arcpy.da.InsertCursor(output_shapefile, ['SHAPE@', 'QUADRANT']) as cursor:
            cursor.insertRow([clipped_geometry, quadrant_name])
        
        print(f"✅ Created {quadrant_name} shapefile: {output_shapefile}")
        print(f"   Area: {clipped_geometry.area}")
    else:
        print(f"⚠️ {quadrant_name} quadrant has no imagery - skipping")

print(f"✅ All boundary-aligned mask shapefiles created successfully in: {output_dir}")
print(f"Files created:")
for quadrant_name, shapefile_name, _, _, _, _ in quadrants:
    output_path = os.path.join(output_dir, shapefile_name)
    if arcpy.Exists(output_path):
        print(f"  - {shapefile_name} ({quadrant_name})")
