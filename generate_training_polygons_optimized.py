import arcpy
import os
import random
import math

def calculate_optimal_polygons(area_sqkm, land_cover_classes=5, min_polygons=50, max_polygons=300):
    """
    Calculate optimal number of training polygons based on area and complexity
    
    Parameters:
    area_sqkm: Area of the section in square kilometers
    land_cover_classes: Expected number of land cover classes
    min_polygons: Minimum polygons regardless of area
    max_polygons: Maximum polygons to avoid oversampling
    """
    
    # Base calculation: ~30-50 polygons per sq km for good statistical sampling
    base_polygons = int(area_sqkm * 40)
    
    # Adjust for number of classes (more classes need more samples)
    class_factor = land_cover_classes / 5.0  # Normalize to 5 classes
    adjusted_polygons = int(base_polygons * class_factor)
    
    # Apply bounds
    optimal_polygons = max(min_polygons, min(max_polygons, adjusted_polygons))
    
    return optimal_polygons

def generate_stratified_polygons(section_raster, output_shapefile, num_polygons=200, 
                               polygon_size=5, land_cover_classes=None):
    """
    Generate stratified random polygons for supervised classification
    
    Parameters:
    section_raster: Input raster for the section
    output_shapefile: Output shapefile for training polygons
    num_polygons: Total number of polygons to generate
    polygon_size: Size of polygons in meters
    land_cover_classes: Optional list of expected land cover types
    """
    
    print(f"=== GENERATING STRATIFIED TRAINING POLYGONS ===")
    print(f"Section: {os.path.basename(section_raster)}")
    print(f"Target polygons: {num_polygons}")
    print(f"Polygon size: {polygon_size}m")
    
    try:
        # Get raster properties
        desc = arcpy.Describe(section_raster)
        extent = desc.extent
        spatial_ref = desc.spatialReference
        
        raster_obj = arcpy.Raster(section_raster)
        cell_size_x = raster_obj.meanCellWidth
        cell_size_y = raster_obj.meanCellHeight
        
        # Calculate raster dimensions
        width = int((extent.XMax - extent.XMin) / cell_size_x)
        height = int((extent.YMax - extent.YMin) / cell_size_y)
        
        print(f"Raster dimensions: {width} x {height} pixels")
        print(f"Extent: {extent.XMax - extent.XMin:.0f}m x {extent.YMax - extent.YMin:.0f}m")
        
        # Strategy 1: Grid-based stratification for even distribution
        grid_polygons = int(num_polygons * 0.7)  # 70% grid-based
        random_polygons = num_polygons - grid_polygons  # 30% pure random
        
        print(f"Strategy: {grid_polygons} grid-based + {random_polygons} random polygons")
        
        # Create output shapefile
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(output_shapefile),
            out_name=os.path.basename(output_shapefile),
            geometry_type="POLYGON",
            spatial_reference=spatial_ref
        )
        
        # Add fields for tracking
        arcpy.management.AddField(output_shapefile, "poly_id", "TEXT", field_length=20)
        arcpy.management.AddField(output_shapefile, "strategy", "TEXT", field_length=20)
        arcpy.management.AddField(output_shapefile, "center_x", "DOUBLE")
        arcpy.management.AddField(output_shapefile, "center_y", "DOUBLE")
        arcpy.management.AddField(output_shapefile, "size_m", "DOUBLE")
        arcpy.management.AddField(output_shapefile, "land_cover", "TEXT", field_length=30)
        arcpy.management.AddField(output_shapefile, "quality", "SHORT")  # 1-5 rating
        arcpy.management.AddField(output_shapefile, "notes", "TEXT", field_length=100)
        
        valid_polygons = []
        polygon_size_cells = polygon_size / min(cell_size_x, cell_size_y)
        buffer_cells = int(polygon_size_cells / 2) + 5  # Extra buffer for edge avoidance
        
        # Strategy 1: Grid-based systematic sampling
        print("Generating grid-based polygons...")
        grid_spacing_x = width // int(math.sqrt(grid_polygons) + 1)
        grid_spacing_y = height // int(math.sqrt(grid_polygons) + 1)
        
        grid_count = 0
        for grid_y in range(buffer_cells, height - buffer_cells, grid_spacing_y):
            for grid_x in range(buffer_cells, width - buffer_cells, grid_spacing_x):
                if grid_count >= grid_polygons:
                    break
                
                # Add some randomness within the grid cell
                jitter_x = random.randint(-grid_spacing_x//4, grid_spacing_x//4)
                jitter_y = random.randint(-grid_spacing_y//4, grid_spacing_y//4)
                
                final_x = max(buffer_cells, min(width - buffer_cells, grid_x + jitter_x))
                final_y = max(buffer_cells, min(height - buffer_cells, grid_y + jitter_y))
                
                # Convert to map coordinates
                map_x = extent.XMin + (final_x * cell_size_x)
                map_y = extent.YMin + (final_y * cell_size_y)
                
                # Check if location is valid
                if is_valid_location(section_raster, map_x, map_y):
                    coords = create_hexagon_polygon(map_x, map_y, polygon_size)
                    
                    valid_polygons.append({
                        'poly_id': f'grid_{grid_count+1:03d}',
                        'strategy': 'grid_based',
                        'center_x': map_x,
                        'center_y': map_y,
                        'size_m': polygon_size,
                        'coords': coords
                    })
                    grid_count += 1
                    
            if grid_count >= grid_polygons:
                break
        
        print(f"Generated {grid_count} grid-based polygons")
        
        # Strategy 2: Pure random sampling for diversity
        print("Generating random polygons...")
        random_count = 0
        attempts = 0
        max_attempts = random_polygons * 5
        
        while random_count < random_polygons and attempts < max_attempts:
            attempts += 1
            
            # Generate random position
            rand_x = extent.XMin + (buffer_cells + random.random() * (width - 2 * buffer_cells)) * cell_size_x
            rand_y = extent.YMin + (buffer_cells + random.random() * (height - 2 * buffer_cells)) * cell_size_y
            
            # Ensure minimum distance from existing polygons (avoid clustering)
            too_close = False
            min_distance = polygon_size * 2  # Minimum 2x polygon size apart
            
            for existing in valid_polygons:
                distance = math.sqrt((rand_x - existing['center_x'])**2 + (rand_y - existing['center_y'])**2)
                if distance < min_distance:
                    too_close = True
                    break
            
            if not too_close and is_valid_location(section_raster, rand_x, rand_y):
                coords = create_hexagon_polygon(rand_x, rand_y, polygon_size)
                
                valid_polygons.append({
                    'poly_id': f'rand_{random_count+1:03d}',
                    'strategy': 'random',
                    'center_x': rand_x,
                    'center_y': rand_y,
                    'size_m': polygon_size,
                    'coords': coords
                })
                random_count += 1
        
        print(f"Generated {random_count} random polygons")
        print(f"Total valid polygons: {len(valid_polygons)}")
        
        # Insert polygons into shapefile
        with arcpy.da.InsertCursor(output_shapefile, 
                                  ["SHAPE@", "poly_id", "strategy", "center_x", "center_y", 
                                   "size_m", "quality"]) as cursor:
            for poly_data in valid_polygons:
                # Create polygon geometry
                polygon_geom = arcpy.Polygon(
                    arcpy.Array([arcpy.Point(x, y) for x, y in poly_data['coords']]), 
                    spatial_ref
                )
                
                cursor.insertRow([
                    polygon_geom,
                    poly_data['poly_id'],
                    poly_data['strategy'],
                    poly_data['center_x'],
                    poly_data['center_y'],
                    poly_data['size_m'],
                    0  # Quality to be filled by user
                ])
        
        print(f"✅ Training polygons saved: {output_shapefile}")
        print(f"Total polygons: {len(valid_polygons)}")
        
        # Generate statistics and recommendations
        generate_training_statistics(output_shapefile, section_raster)
        
        return output_shapefile, len(valid_polygons)
        
    except Exception as e:
        print(f"❌ Error generating polygons: {e}")
        return None, 0

def is_valid_location(raster_path, x, y):
    """Check if a location has valid data (not NoData)"""
    try:
        result = arcpy.management.GetCellValue(raster_path, f"{x} {y}")
        cell_value = result.getOutput(0)
        return cell_value != "NoData" and cell_value != ""
    except:
        return False

def create_hexagon_polygon(center_x, center_y, size):
    """Create hexagonal polygon coordinates"""
    coords = []
    radius = size / 2
    for i in range(6):
        angle = 2 * math.pi * i / 6
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        coords.append((x, y))
    coords.append(coords[0])  # Close the polygon
    return coords

def generate_training_statistics(shapefile, raster):
    """Generate statistics and recommendations for the training data"""
    print("\n=== TRAINING DATA STATISTICS ===")
    
    # Count polygons by strategy
    grid_count = 0
    random_count = 0
    
    with arcpy.da.SearchCursor(shapefile, ["strategy"]) as cursor:
        for row in cursor:
            if row[0] == "grid_based":
                grid_count += 1
            else:
                random_count += 1
    
    total = grid_count + random_count
    
    print(f"Grid-based polygons: {grid_count} ({grid_count/total*100:.1f}%)")
    print(f"Random polygons: {random_count} ({random_count/total*100:.1f}%)")
    print(f"Total polygons: {total}")
    
    # Calculate density
    raster_desc = arcpy.Describe(raster)
    extent = raster_desc.extent
    area_sqkm = ((extent.XMax - extent.XMin) * (extent.YMax - extent.YMin)) / 1000000
    density = total / area_sqkm
    
    print(f"Section area: {area_sqkm:.1f} sq km")
    print(f"Polygon density: {density:.1f} polygons/sq km")
    
    # Recommendations
    print("\n=== RECOMMENDATIONS ===")
    if density < 20:
        print("⚠️  Low density - consider adding more polygons for better accuracy")
    elif density > 100:
        print("⚠️  High density - may be over-sampling, could reduce for efficiency")
    else:
        print("✅ Good polygon density for classification")
    
    print(f"Recommended land cover classes: 4-6 classes")
    print(f"Minimum samples per class: {total//6} polygons")
    print(f"Recommended training approach: Visual interpretation + field validation")

# Example usage for each section
def process_all_sections(sections_folder, output_folder):
    """Process all section rasters to generate training polygons"""
    print("=== PROCESSING ALL SECTIONS FOR TRAINING DATA ===")
    
    section_files = [f for f in os.listdir(sections_folder) if f.endswith('.tif')]
    print(f"Found {len(section_files)} sections to process")
    
    training_folder = os.path.join(output_folder, "training_polygons")
    os.makedirs(training_folder, exist_ok=True)
    
    results = []
    
    for section_file in section_files:
        section_path = os.path.join(sections_folder, section_file)
        section_name = os.path.splitext(section_file)[0]
        output_shp = os.path.join(training_folder, f"{section_name}_training.shp")
        
        print(f"\nProcessing {section_name}...")
        
        # Calculate area to determine optimal polygon count
        desc = arcpy.Describe(section_path)
        extent = desc.extent
        area_sqkm = ((extent.XMax - extent.XMin) * (extent.YMax - extent.YMin)) / 1000000
        
        optimal_polygons = calculate_optimal_polygons(area_sqkm)
        print(f"Section area: {area_sqkm:.1f} sq km")
        print(f"Optimal polygons: {optimal_polygons}")
        
        # Generate polygons
        output_path, polygon_count = generate_stratified_polygons(
            section_raster=section_path,
            output_shapefile=output_shp,
            num_polygons=optimal_polygons,
            polygon_size=5  # 5m polygons for detailed classification
        )
        
        if output_path:
            results.append({
                'section': section_name,
                'area_sqkm': area_sqkm,
                'polygons': polygon_count,
                'shapefile': output_path
            })
    
    # Create summary report
    summary_file = os.path.join(output_folder, "training_data_summary.txt")
    with open(summary_file, 'w') as f:
        f.write("TRAINING DATA GENERATION SUMMARY\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        total_polygons = sum(r['polygons'] for r in results)
        total_area = sum(r['area_sqkm'] for r in results)
        
        f.write(f"Total sections: {len(results)}\n")
        f.write(f"Total area: {total_area:.1f} sq km\n")
        f.write(f"Total training polygons: {total_polygons}\n")
        f.write(f"Average density: {total_polygons/total_area:.1f} polygons/sq km\n\n")
        
        f.write("SECTION DETAILS:\n")
        for result in results:
            f.write(f"{result['section']}:\n")
            f.write(f"  Area: {result['area_sqkm']:.1f} sq km\n")
            f.write(f"  Polygons: {result['polygons']}\n")
            f.write(f"  Density: {result['polygons']/result['area_sqkm']:.1f}/sq km\n")
            f.write(f"  Shapefile: {result['shapefile']}\n\n")
    
    print(f"\n✅ All sections processed!")
    print(f"Training polygons folder: {training_folder}")
    print(f"Summary report: {summary_file}")
    
    return results

if __name__ == "__main__":
    # Update these paths
    sections_raster_folder = r"C:\path\to\section_rasters"  # From previous step
    output_project_folder = r"C:\path\to\classification_project"  # Update this
    
    # Process all sections
    results = process_all_sections(sections_raster_folder, output_project_folder)
    
    print("\n=== TRAINING DATA GENERATION COMPLETE ===")
    print("NEXT STEPS:")
    print("1. Assign each section to a team member")
    print("2. Each person reviews and labels their training polygons")
    print("3. Run supervised classification on each section")
    print("4. Combine results using the mosaic combination script")
