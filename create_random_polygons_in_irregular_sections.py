import arcpy
import os
import random
import math

# --- CONFIGURATION ---
irregular_sections_folder = r"C:\Users\c72liu\Desktop\irregular_sections"  # Folder with your irregular section shapefiles
output_folder = r"C:\Users\c72liu\Desktop\random_polygons_final"  # Where to save random polygons
num_random_polygons = 300  # Number of random polygons per section
polygon_diameter = 6  # Diameter of each random polygon in meters
polygon_radius = polygon_diameter / 2  # 3m radius
# ---------------------

def create_random_irregular_polygon(center_x, center_y, base_radius, spatial_ref):
    """Create a random irregular polygon around a center point"""
    # Number of vertices for the irregular polygon
    num_vertices = random.randint(8, 15)  # Random between 8-15 vertices for more variety
    
    vertices = []
    angle_step = 2 * math.pi / num_vertices
    
    for i in range(num_vertices):
        # Base angle for this vertex
        angle = i * angle_step
        
        # Add random variation to angle (±20 degrees)
        angle_variation = random.uniform(-0.35, 0.35)  # ±20 degrees in radians
        actual_angle = angle + angle_variation
        
        # Add random variation to radius (60% to 140% of base radius)
        radius_variation = random.uniform(0.6, 1.4)
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

# Create output directory
os.makedirs(output_folder, exist_ok=True)

print("🎉 Creating RANDOM POLYGONS in each irregular section!")
print(f"Will create {num_random_polygons} random polygons per section")
print(f"Each polygon will be {polygon_diameter}m diameter with random irregular shape")

# List of irregular section shapefile names
section_shapefiles = [
    "irregular_topleft_section.shp",
    "irregular_topright_section.shp", 
    "irregular_bottomleft_section.shp",
    "irregular_bottomright_section.shp"
]

print(f"Looking for irregular sections in: {irregular_sections_folder}")

# Get spatial reference from first available section
spatial_ref = None
for section_name in section_shapefiles:
    section_path = os.path.join(irregular_sections_folder, section_name)
    if arcpy.Exists(section_path):
        desc = arcpy.Describe(section_path)
        spatial_ref = desc.spatialReference
        break

if not spatial_ref:
    print("❌ No irregular section shapefiles found!")
    exit()

print(f"✅ Using spatial reference: {spatial_ref.name}")

# Process each irregular section
total_created = 0
for section_name in section_shapefiles:
    section_path = os.path.join(irregular_sections_folder, section_name)
    
    if arcpy.Exists(section_path):
        print(f"\n🎲 Creating random polygons for {section_name}...")
        
        # Read the irregular section geometry
        print(f"  📖 Reading irregular section geometry...")
        section_polygons = []
        with arcpy.da.SearchCursor(section_path, ["SHAPE@", "SECTION"]) as cursor:
            for row in cursor:
                if row[0]:
                    section_polygons.append((row[0], row[1]))  # (geometry, section_name)
        
        if section_polygons:
            section_polygon, section_id = section_polygons[0]  # Get the first polygon
            
            print(f"  ✅ Section area: {section_polygon.area:.0f} m²")
            
            # Get the bounding box of the section
            section_extent = section_polygon.extent
            
            # Create output shapefile for random polygons
            output_name = f"random_polygons_{section_id}.shp"
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
            
            # Generate random polygons within the irregular section
            print(f"  🎲 Generating {num_random_polygons} random irregular polygons...")
            successful_polygons = 0
            attempts = 0
            max_attempts = num_random_polygons * 15  # Try up to 15x the desired number
            
            with arcpy.da.InsertCursor(output_path, ['SHAPE@', 'SECTION', 'POLYGON_ID', 'AREA_M2', 'LAND_COVER']) as cursor:
                while successful_polygons < num_random_polygons and attempts < max_attempts:
                    attempts += 1
                    
                    # Generate random point within section extent (with buffer)
                    buffer = polygon_radius * 2  # Keep polygons away from edges
                    random_x = random.uniform(section_extent.XMin + buffer, section_extent.XMax - buffer)
                    random_y = random.uniform(section_extent.YMin + buffer, section_extent.YMax - buffer)
                    
                    # Create a random irregular polygon
                    random_polygon = create_random_irregular_polygon(random_x, random_y, polygon_radius, spatial_ref)
                    
                    # Check if the random polygon is within the irregular section
                    if section_polygon.contains(random_polygon):
                        # Polygon is completely within the section
                        final_polygon = random_polygon
                    elif section_polygon.overlaps(random_polygon):
                        # Clip the polygon to the section boundary
                        final_polygon = section_polygon.intersect(random_polygon, 4)
                    else:
                        # Polygon is outside the section, skip it
                        continue
                    
                    if final_polygon and final_polygon.area > 0:
                        successful_polygons += 1
                        
                        # Leave land cover field empty for manual labeling
                        land_cover = ""  # Empty string - ready for your manual classification
                        
                        cursor.insertRow([
                            final_polygon, 
                            section_id, 
                            successful_polygons,
                            final_polygon.area,
                            land_cover
                        ])
                        
                        # Progress update every 75 polygons
                        if successful_polygons % 75 == 0:
                            print(f"    Created {successful_polygons}/{num_random_polygons} polygons...")
            
            print(f"  ✅ Successfully created {successful_polygons} random irregular polygons")
            print(f"     Output: {output_path}")
            print(f"     Attempts made: {attempts}")
            total_created += successful_polygons
            
            if successful_polygons < num_random_polygons:
                print(f"  ⚠️ Only created {successful_polygons}/{num_random_polygons} polygons")
                print(f"     (Section area might be limited or narrow)")
        else:
            print(f"  ⚠️ No polygons found in {section_name}")
    else:
        print(f"⚠️ Section shapefile not found: {section_path}")

print(f"\n🎉 RANDOM POLYGON GENERATION COMPLETE!")
print(f"Random polygons saved to: {output_folder}")

# List final results
print(f"\n📁 Random polygon files created:")
if os.path.exists(output_folder):
    files = [f for f in os.listdir(output_folder) if f.endswith('.shp')]
    if files:
        grand_total = 0
        for file in files:
            file_path = os.path.join(output_folder, file)
            try:
                count = int(arcpy.management.GetCount(file_path).getOutput(0))
                grand_total += count
                print(f"  🎲 {file} ({count} polygons)")
            except:
                print(f"  🎲 {file}")
        print(f"\n📊 Total random polygons created: {grand_total}")
        print(f"📊 Target was: {len(section_shapefiles) * num_random_polygons}")
    else:
        print("  No files created")
else:
    print("  Output folder not found")

print(f"\n🎯 SUCCESS! Random irregular polygons distributed across your 4 sections!")
print(f"🎯 Each polygon is {polygon_diameter}m diameter with random irregular shape")
print(f"🎯 Land cover field is empty - ready for your manual classification!")
print(f"🎯 4 separate files - one for each irregular section!")
print(f"🎯 Add them to your map to see the random sampling locations!")
