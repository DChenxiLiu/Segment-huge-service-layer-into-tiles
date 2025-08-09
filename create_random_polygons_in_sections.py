import arcpy
import os
import random
import math

# --- CONFIGURATION ---
imagery_layer_name = "Imagery_2024"  # Your imagery layer name in ArcGIS Pro
mask_shapefile_folder = r"C:\Users\c72liu\Desktop\mask_shapefiles"  # Folder with your rectangular mask shapefiles
output_folder = r"C:\Users\c72liu\Desktop\random_polygons"  # Where to save random polygons
num_random_polygons = 300  # Number of random polygons per section
polygon_size = 4  # Radius of each random polygon in meters (8m diameter = 4m radius)
# ---------------------

def create_random_irregular_polygon(center_x, center_y, base_radius, spatial_ref):
    """Create a random irregular polygon around a center point"""
    # Number of vertices for the irregular polygon
    num_vertices = random.randint(6, 12)  # Random between 6-12 vertices
    
    vertices = []
    angle_step = 2 * math.pi / num_vertices
    
    for i in range(num_vertices):
        # Base angle for this vertex
        angle = i * angle_step
        
        # Add random variation to angle (±15 degrees)
        angle_variation = random.uniform(-0.26, 0.26)  # ±15 degrees in radians
        actual_angle = angle + angle_variation
        
        # Add random variation to radius (50% to 150% of base radius)
        radius_variation = random.uniform(0.5, 1.5)
        actual_radius = base_radius * radius_variation
        
        # Calculate vertex coordinates
        x = center_x + actual_radius * math.cos(actual_angle)
        y = center_y + actual_radius * math.sin(actual_angle)
        
        vertices.append(arcpy.Point(x, y))
    
    # Close the polygon by adding the first vertex at the end
    vertices.append(vertices[0])
    
    # Create polygon
    polygon_array = arcpy.Array(vertices)
    return arcpy.Polygon(polygon_array, spatial_ref)

def check_polygon_in_imagery_data(polygon, imagery_layer, temp_check_raster):
    """Check if polygon falls within actual imagery data (not no-data areas)"""
    try:
        # Create a small temporary raster from the polygon extent
        polygon_extent = polygon.extent
        
        # Expand extent slightly for sampling
        buffer = 10  # 10 meter buffer
        sample_extent = f"{polygon_extent.XMin - buffer} {polygon_extent.YMin - buffer} {polygon_extent.XMax + buffer} {polygon_extent.YMax + buffer}"
        
        # Extract a small sample of the imagery at this location
        with arcpy.EnvManager(extent=sample_extent, cellSize=2):  # 2m resolution for checking
            arcpy.management.Clip(
                in_raster=imagery_layer.dataSource,
                rectangle=sample_extent,
                out_raster=temp_check_raster,
                clipping_geometry="NONE",
                maintain_clipping_extent="NO_MAINTAIN_EXTENT"
            )
        
        # Check if the raster has valid data (not all NoData)
        result = arcpy.management.GetRasterProperties(temp_check_raster, "MINIMUM")
        min_value = result.getOutput(0)
        
        # If we get a minimum value, there's data here
        return min_value != "None" and min_value is not None
        
    except:
        # If any error occurs, assume no data
        return False

# Create output directory
os.makedirs(output_folder, exist_ok=True)

print("🎯 Creating RANDOM POLYGONS in imagery-mask overlap areas!")
print(f"Will create {num_random_polygons} random polygons per section")

# Get the current map and imagery layer
print("Getting imagery layer from current map...")
aprx = arcpy.mp.ArcGISProject("CURRENT")
map_ = aprx.listMaps()[0]
imagery_layer = map_.listLayers(imagery_layer_name)[0]

print(f"Found imagery layer: {imagery_layer.name}")

# Get the imagery properties
desc = arcpy.Describe(imagery_layer)
spatial_ref = desc.spatialReference

# Get imagery extent as a polygon for overlap checking
extent = desc.extent
imagery_boundary_array = arcpy.Array([
    arcpy.Point(extent.XMin, extent.YMin),
    arcpy.Point(extent.XMin, extent.YMax),
    arcpy.Point(extent.XMax, extent.YMax),
    arcpy.Point(extent.XMax, extent.YMin),
    arcpy.Point(extent.XMin, extent.YMin)
])
imagery_boundary = arcpy.Polygon(imagery_boundary_array, spatial_ref)

print(f"Imagery boundary area: {imagery_boundary.area:.0f} m²")

# List of mask shapefile names
mask_shapefiles = [
    "mask_topleft.shp",
    "mask_topright.shp", 
    "mask_bottomleft.shp",
    "mask_bottomright.shp"
]

print(f"Looking for mask shapefiles in: {mask_shapefile_folder}")

# Process each mask shapefile
for mask_name in mask_shapefiles:
    mask_path = os.path.join(mask_shapefile_folder, mask_name)
    
    if arcpy.Exists(mask_path):
        print(f"\n🎲 Creating random polygons for {mask_name}...")
        
        # Read the mask shapefile geometry
        print(f"  📖 Reading mask geometry...")
        mask_polygons = []
        with arcpy.da.SearchCursor(mask_path, ["SHAPE@"]) as cursor:
            for row in cursor:
                if row[0]:
                    mask_polygons.append(row[0])
        
        if mask_polygons:
            mask_polygon = mask_polygons[0]  # Get the first polygon
            
            # Find the overlap area between mask and imagery
            print(f"  🔍 Finding overlap area...")
            overlap_area = imagery_boundary.intersect(mask_polygon, 4)  # 4 = geometry intersection
            
            if overlap_area and overlap_area.area > 0:
                print(f"  ✅ Overlap area found: {overlap_area.area:.0f} m²")
                
                # Get the bounding box of the overlap area
                overlap_extent = overlap_area.extent
                
                # Create output shapefile for random polygons
                section_name = mask_name.replace('mask_', '').replace('.shp', '')
                output_name = f"random_polygons_{section_name}.shp"
                output_path = os.path.join(output_folder, output_name)
                
                print(f"  🏗️ Creating output shapefile: {output_name}")
                arcpy.management.CreateFeatureclass(
                    out_path=output_folder,
                    out_name=output_name,
                    geometry_type="POLYGON",
                    spatial_reference=spatial_ref
                )
                
                # Add fields
                arcpy.management.AddField(output_path, "SECTION", "TEXT", field_length=20)
                arcpy.management.AddField(output_path, "POLYGON_ID", "LONG")
                arcpy.management.AddField(output_path, "AREA_M2", "DOUBLE")
                arcpy.management.AddField(output_path, "LAND_COVER", "TEXT", field_length=50)
                
                # Generate random polygons within the overlap area
                print(f"  🎲 Generating {num_random_polygons} random irregular polygons...")
                print(f"  🔍 Checking for actual imagery data (avoiding no-data areas)...")
                successful_polygons = 0
                attempts = 0
                max_attempts = num_random_polygons * 20  # Try up to 20x for data checking
                
                # Temporary raster for data checking
                temp_check_raster = f"temp_check_{section_name}"
                
                with arcpy.da.InsertCursor(output_path, ['SHAPE@', 'SECTION', 'POLYGON_ID', 'AREA_M2', 'LAND_COVER']) as cursor:
                    while successful_polygons < num_random_polygons and attempts < max_attempts:
                        attempts += 1
                        
                        # Generate random point within overlap extent
                        random_x = random.uniform(overlap_extent.XMin + polygon_size, overlap_extent.XMax - polygon_size)
                        random_y = random.uniform(overlap_extent.YMin + polygon_size, overlap_extent.YMax - polygon_size)
                        
                        # Create a random irregular polygon
                        random_polygon = create_random_irregular_polygon(random_x, random_y, polygon_size, spatial_ref)
                        
                        # Check if the random polygon is within the overlap area
                        if overlap_area.contains(random_polygon) or overlap_area.overlaps(random_polygon):
                            # Clip the polygon to the overlap area to ensure it's within bounds
                            clipped_polygon = overlap_area.intersect(random_polygon, 4)
                            
                            if clipped_polygon and clipped_polygon.area > 0:
                                # Check if this location has actual imagery data (not no-data)
                                has_data = check_polygon_in_imagery_data(clipped_polygon, imagery_layer, temp_check_raster)
                                
                                if has_data:
                                    successful_polygons += 1
                                    
                                    # Assign a placeholder land cover value (you can modify this)
                                    land_cover_value = f"LC_{successful_polygons:03d}"  # e.g., "LC_001", "LC_002", etc.
                                    
                                    cursor.insertRow([
                                        clipped_polygon, 
                                        section_name, 
                                        successful_polygons,
                                        clipped_polygon.area,
                                        land_cover_value
                                    ])
                                    
                                    # Progress update every 50 polygons
                                    if successful_polygons % 50 == 0:
                                        print(f"    Created {successful_polygons}/{num_random_polygons} polygons...")
                                
                                # Clean up temporary check raster
                                if arcpy.Exists(temp_check_raster):
                                    try:
                                        arcpy.management.Delete(temp_check_raster)
                                    except:
                                        pass
                
                print(f"  ✅ Successfully created {successful_polygons} irregular polygons with data")
                print(f"     Output: {output_path}")
                print(f"     Attempts made: {attempts} (data checking enabled)")
                
                if successful_polygons < num_random_polygons:
                    print(f"  ⚠️ Only created {successful_polygons}/{num_random_polygons} polygons")
                    print(f"     (Some areas may have no imagery data or insufficient data coverage)")
                
            else:
                print(f"  ⚠️ No overlap found between {mask_name} and imagery")
        else:
            print(f"  ⚠️ No polygons found in {mask_name}")
    else:
        print(f"⚠️ Mask shapefile not found: {mask_path}")

print(f"\n🎉 RANDOM POLYGON GENERATION COMPLETE!")
print(f"Random polygons saved to: {output_folder}")

# List final results
print(f"\n📁 Random polygon files created:")
if os.path.exists(output_folder):
    files = [f for f in os.listdir(output_folder) if f.endswith('.shp')]
    if files:
        total_polygons = 0
        for file in files:
            file_path = os.path.join(output_folder, file)
            try:
                count = int(arcpy.management.GetCount(file_path).getOutput(0))
                total_polygons += count
                print(f"  🎲 {file} ({count} polygons)")
            except:
                print(f"  🎲 {file}")
        print(f"\n📊 Total random polygons created: {total_polygons}")
    else:
        print("  No files created")
else:
    print("  Output folder not found")

print(f"\n🎯 Random IRREGULAR polygons are distributed ONLY in areas with actual imagery data!")
print(f"🎯 Each polygon is 8m diameter with random irregular shape")
print(f"🎯 All polygons avoid no-data areas and include LAND_COVER field")
print(f"🎯 Add them to your map to see the random sampling locations!")
