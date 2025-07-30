# ArcPy version - compatible with ArcGIS Pro

import arcpy
import os
import random
import math

# --- CONFIGURATION ---
tiles_dir = r"directory/path/to/the/tiles  # Folder containing tiles (update this path)
num_polygons = 50  # Reduced number since polygons contain more information than points
polygon_size = 2   # Size of polygons in meters (2m x 2m squares)
polygon_shape = 'hexagon'  # Options: 'square', 'circle', 'hexagon'
# ---------------------

tile_files = [f for f in os.listdir(tiles_dir) if f.lower().endswith('.tif')]

def create_polygon_coordinates(center_x, center_y, size, shape='square'):
    """Create different polygon shapes centered at given coordinates"""
    half_size = size / 2
    
    if shape == 'square':
        # Create a square polygon
        coords = [
            (center_x - half_size, center_y - half_size),
            (center_x + half_size, center_y - half_size),
            (center_x + half_size, center_y + half_size),
            (center_x - half_size, center_y + half_size),
            (center_x - half_size, center_y - half_size)  # Close the polygon
        ]
        return coords
    
    elif shape == 'circle':
        # Create a circular polygon (approximated with many points)
        coords = []
        radius = half_size
        for i in range(16):
            angle = 2 * math.pi * i / 16
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            coords.append((x, y))
        coords.append(coords[0])  # Close the polygon
        return coords
    
    elif shape == 'hexagon':
        # Create a hexagonal polygon
        coords = []
        radius = half_size
        for i in range(6):
            angle = 2 * math.pi * i / 6
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            coords.append((x, y))
        coords.append(coords[0])  # Close the polygon
        return coords
    
    else:
        # Default to square
        return create_polygon_coordinates(center_x, center_y, size, 'square')

for tile_file in tile_files:
    raster_path = os.path.join(tiles_dir, tile_file)
    output_shp = os.path.splitext(tile_file)[0] + f"_polygons_{polygon_shape}.shp"
    output_shp = os.path.join(tiles_dir, output_shp)
    
    try:
        # Get raster properties using ArcPy
        desc = arcpy.Describe(raster_path)
        extent = desc.extent
        spatial_ref = desc.spatialReference
        
        # Get cell size
        raster_obj = arcpy.Raster(raster_path)
        cell_size_x = raster_obj.meanCellWidth
        cell_size_y = raster_obj.meanCellHeight
        
        # Calculate raster dimensions
        width = int((extent.XMax - extent.XMin) / cell_size_x)
        height = int((extent.YMax - extent.YMin) / cell_size_y)
        
        # Convert polygon size from meters to cells
        polygon_size_cells = polygon_size / min(cell_size_x, cell_size_y)
        buffer_cells = int(polygon_size_cells / 2) + 1
        
        # Generate random coordinates
        valid_polygons = []
        polygon_coords_list = []
        
        attempts = 0
        while len(valid_polygons) < num_polygons and attempts < num_polygons * 3:
            attempts += 1
            
            # Generate random position (avoiding edges)
            rand_x = extent.XMin + (buffer_cells + random.random() * (width - 2 * buffer_cells)) * cell_size_x
            rand_y = extent.YMin + (buffer_cells + random.random() * (height - 2 * buffer_cells)) * cell_size_y
            
            # Create polygon coordinates
            coords = create_polygon_coordinates(rand_x, rand_y, polygon_size, polygon_shape)
            
            # Check if location is valid (not nodata)
            try:
                # Sample the center point to check for nodata
                result = arcpy.management.GetCellValue(raster_path, f"{rand_x} {rand_y}")
                cell_value = result.getOutput(0)
                
                if cell_value != "NoData" and cell_value != "":
                    valid_polygons.append({
                        'poly_id': f'poly_{len(valid_polygons)+1:03d}',
                        'center_x': rand_x,
                        'center_y': rand_y,
                        'size_m': polygon_size,
                        'shape': polygon_shape,
                        'coords': coords
                    })
                    polygon_coords_list.append(coords)
            except:
                continue
        
        # Create shapefile using ArcPy
        if valid_polygons:
            # Create feature class
            arcpy.management.CreateFeatureclass(
                out_path=os.path.dirname(output_shp),
                out_name=os.path.basename(output_shp),
                geometry_type="POLYGON",
                spatial_reference=spatial_ref
            )
            
            # Add fields
            arcpy.management.AddField(output_shp, "poly_id", "TEXT", field_length=20)
            arcpy.management.AddField(output_shp, "center_x", "DOUBLE")
            arcpy.management.AddField(output_shp, "center_y", "DOUBLE")
            arcpy.management.AddField(output_shp, "size_m", "DOUBLE")
            arcpy.management.AddField(output_shp, "shape_type", "TEXT", field_length=20)
            
            # Insert polygons
            with arcpy.da.InsertCursor(output_shp, ["SHAPE@", "poly_id", "center_x", "center_y", "size_m", "shape_type"]) as cursor:
                for poly_data in valid_polygons:
                    # Create polygon geometry
                    polygon_geom = arcpy.Polygon(arcpy.Array([arcpy.Point(x, y) for x, y in poly_data['coords']]), spatial_ref)
                    
                    cursor.insertRow([
                        polygon_geom,
                        poly_data['poly_id'],
                        poly_data['center_x'],
                        poly_data['center_y'],
                        poly_data['size_m'],
                        poly_data['shape']
                    ])
            
            print(f"Saved {len(valid_polygons)} random {polygon_shape} polygons ({polygon_size}m) as {output_shp}")
        else:
            print(f"No valid polygons generated for {tile_file}")
            
    except Exception as e:
        print(f"Error processing {tile_file}: {str(e)}")
        continue
print(f"\nPolygon generation complete!")
print(f"Generated {polygon_shape} polygons of {polygon_size}m size using ArcPy")
print("Each polygon contains multiple pixels for more robust supervised classification.")
print("Compatible with ArcGIS Pro environment - no external libraries required.")