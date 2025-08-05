import arcpy
import os

def create_imagery_boundary_mask(input_raster, output_shapefile, simplify_tolerance=10):
    """
    Create a boundary polygon from the imagery to mask out NoData areas
    
    Parameters:
    input_raster: Path to imagery mosaic OR ArcGIS layer name OR web service URL
    output_shapefile: Output shapefile for the boundary
    simplify_tolerance: Simplification tolerance in meters (10m recommended)
    """
    
    print("=== CREATING IMAGERY BOUNDARY MASK ===")
    print(f"Input source: {input_raster}")
    print(f"Output shapefile: {output_shapefile}")
    
    # Handle different input types
    if input_raster.startswith("http"):
        print("Input detected as web service URL")
        # For web service, we'll use a different approach
        return create_boundary_from_web_service(input_raster, output_shapefile, simplify_tolerance)
    elif os.path.isfile(input_raster):
        print("Input detected as file path")
        imagery_layer = input_raster
    else:
        print("Input detected as layer name - looking in current ArcGIS Pro project")
        # Try to find the layer in current project
        project = arcpy.mp.ArcGISProject("CURRENT")
        map_ = project.activeMap or project.listMaps()[0]
        
        layer_found = False
        for lyr in map_.listLayers():
            if lyr.name == input_raster:
                imagery_layer = lyr
                layer_found = True
                break
        
        if not layer_found:
            print(f"❌ Layer '{input_raster}' not found in current project")
            print("Available layers:")
            for lyr in map_.listLayers():
                print(f"  - {lyr.name}")
            return None
    
    try:
        # Step 1: Create a binary raster (data vs nodata)
        print("Step 1: Creating binary mask...")
        temp_binary = "in_memory/binary_mask"
        
        # Use a more robust approach for different data types
        try:
            # Method 1: Try with Spatial Analyst Con tool
            arcpy.gp.Con_sa(imagery_layer, "1", temp_binary, "", "VALUE >= 0")
        except:
            try:
                # Method 2: Use Set Null and then convert
                temp_notnull = "in_memory/notnull_mask"
                arcpy.gp.SetNull_sa(imagery_layer, "1", temp_notnull, "VALUE < 0")
                arcpy.gp.Con_sa(temp_notnull, "1", temp_binary, "", "VALUE >= 0")
            except:
                # Method 3: Use raster calculator
                expression = f'Con(IsNull("{imagery_layer}"), 0, 1)'
                arcpy.gp.RasterCalculator_sa(expression, temp_binary)
        
        # Step 2: Convert raster to polygon
        print("Step 2: Converting to polygons...")
        temp_poly = "in_memory/temp_polygons"
        arcpy.conversion.RasterToPolygon(
            in_raster=temp_binary,
            out_polygon_features=temp_poly,
            simplify="SIMPLIFY",
            raster_field="VALUE"
        )
        
        # Step 3: Dissolve all polygons into single boundary
        print("Step 3: Dissolving polygons...")
        temp_dissolved = "in_memory/dissolved"
        arcpy.management.Dissolve(
            in_features=temp_poly,
            out_feature_class=temp_dissolved,
            dissolve_field="gridcode"
        )
        
        # Step 4: Simplify the boundary
        print(f"Step 4: Simplifying boundary (tolerance: {simplify_tolerance}m)...")
        arcpy.cartography.SimplifyPolygon(
            in_features=temp_dissolved,
            out_feature_class=output_shapefile,
            algorithm="POINT_REMOVE",
            tolerance=f"{simplify_tolerance} Meters",
            minimum_area="0 SquareMeters",
            error_option="RESOLVE_ERRORS",
            collapsed_point_option="NO_KEEP"
        )
        
        # Step 5: Add useful fields
        print("Step 5: Adding attribute fields...")
        arcpy.management.AddField(output_shapefile, "Area_SqKm", "DOUBLE")
        arcpy.management.AddField(output_shapefile, "Perimeter_Km", "DOUBLE")
        arcpy.management.AddField(output_shapefile, "Created_Date", "DATE")
        
        # Calculate area and perimeter
        with arcpy.da.UpdateCursor(output_shapefile, ["SHAPE@", "Area_SqKm", "Perimeter_Km", "Created_Date"]) as cursor:
            for row in cursor:
                shape = row[0]
                area_sqm = shape.area
                perimeter_m = shape.length
                
                row[1] = area_sqm / 1000000  # Convert to sq km
                row[2] = perimeter_m / 1000   # Convert to km
                row[3] = arcpy.time.ParseDateTimeString("today")
                cursor.updateRow(row)
        
        print("✅ Boundary mask created successfully!")
        
        # Get statistics
        with arcpy.da.SearchCursor(output_shapefile, ["Area_SqKm", "Perimeter_Km"]) as cursor:
            for row in cursor:
                print(f"Imagery area: {row[0]:.1f} sq km")
                print(f"Perimeter: {row[1]:.1f} km")
        
        return output_shapefile
        
    except Exception as e:
        print(f"❌ Error creating boundary mask: {e}")
        return None

def create_boundary_from_web_service(service_url, output_shapefile, simplify_tolerance=10):
    """
    Create boundary from ArcGIS Image Service URL
    """
    print("=== CREATING BOUNDARY FROM WEB SERVICE ===")
    
    try:
        # Add the image service as a layer
        print("Adding image service layer...")
        temp_layer_name = "Temp_Imagery_Service"
        
        # Make the image service layer
        arcpy.management.MakeImageServerLayer(
            in_image_service=service_url,
            out_imageserver_layer=temp_layer_name
        )
        
        print(f"✅ Image service layer created: {temp_layer_name}")
        
        # Get the extent from the service
        desc = arcpy.Describe(temp_layer_name)
        extent = desc.extent
        
        print(f"Service extent: {extent.XMin:.0f}, {extent.YMin:.0f}, {extent.XMax:.0f}, {extent.YMax:.0f}")
        print(f"Spatial Reference: {desc.spatialReference.name}")
        
        # For image services, create boundary from extent and known data areas
        # Create a polygon from the service extent
        boundary_points = [
            arcpy.Point(extent.XMin, extent.YMin),
            arcpy.Point(extent.XMax, extent.YMin),
            arcpy.Point(extent.XMax, extent.YMax),
            arcpy.Point(extent.XMin, extent.YMax)
        ]
        
        # Create the boundary polygon
        boundary_polygon = arcpy.Polygon(arcpy.Array(boundary_points), desc.spatialReference)
        
        # Create the output shapefile
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(output_shapefile),
            out_name=os.path.basename(output_shapefile),
            geometry_type="POLYGON",
            spatial_reference=desc.spatialReference
        )
        
        # Add fields
        arcpy.management.AddField(output_shapefile, "Area_SqKm", "DOUBLE")
        arcpy.management.AddField(output_shapefile, "Perimeter_Km", "DOUBLE")
        arcpy.management.AddField(output_shapefile, "Source", "TEXT", field_length=100)
        arcpy.management.AddField(output_shapefile, "Created_Date", "DATE")
        
        # Insert the boundary polygon
        with arcpy.da.InsertCursor(output_shapefile, 
                                  ["SHAPE@", "Area_SqKm", "Perimeter_Km", "Source", "Created_Date"]) as cursor:
            area_sqm = boundary_polygon.area
            perimeter_m = boundary_polygon.length
            
            cursor.insertRow([
                boundary_polygon,
                area_sqm / 1000000,  # Convert to sq km
                perimeter_m / 1000,   # Convert to km
                service_url,
                arcpy.time.ParseDateTimeString("today")
            ])
        
        print("✅ Boundary shapefile created from web service!")
        print(f"Area: {area_sqm / 1000000:.1f} sq km")
        print(f"Perimeter: {perimeter_m / 1000:.1f} km")
        
        # Clean up temporary layer
        arcpy.management.Delete(temp_layer_name)
        
        return output_shapefile
        
    except Exception as e:
        print(f"❌ Error creating boundary from web service: {e}")
        return None

def clip_tiles_with_boundary(tiles_folder, boundary_shapefile, output_folder):
    """
    Process existing tiles to remove areas outside the boundary
    """
    print("\n=== CLIPPING TILES WITH BOUNDARY ===")
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    # Get list of tiles
    tile_files = [f for f in os.listdir(tiles_folder) if f.endswith('.tif')]
    print(f"Found {len(tile_files)} tiles to process")
    
    processed = 0
    skipped = 0
    
    for i, tile_file in enumerate(tile_files):
        tile_path = os.path.join(tiles_folder, tile_file)
        output_path = os.path.join(output_folder, tile_file)
        
        if i % 100 == 0:
            print(f"Processing tile {i+1}/{len(tile_files)}: {tile_file}")
        
        try:
            # Check if tile intersects with boundary
            tile_desc = arcpy.Describe(tile_path)
            tile_extent = tile_desc.extent
            
            # Create temporary extent polygon
            temp_extent = arcpy.Polygon(arcpy.Array([
                arcpy.Point(tile_extent.XMin, tile_extent.YMin),
                arcpy.Point(tile_extent.XMax, tile_extent.YMin),
                arcpy.Point(tile_extent.XMax, tile_extent.YMax),
                arcpy.Point(tile_extent.XMin, tile_extent.YMax)
            ]), tile_desc.spatialReference)
            
            # Check intersection with boundary
            with arcpy.da.SearchCursor(boundary_shapefile, ["SHAPE@"]) as cursor:
                boundary_shape = next(cursor)[0]
                
                if temp_extent.overlaps(boundary_shape) or temp_extent.within(boundary_shape):
                    # Tile intersects - clip it
                    arcpy.management.Clip(
                        in_raster=tile_path,
                        rectangle="",
                        out_raster=output_path,
                        in_template_dataset=boundary_shapefile,
                        nodata_value="-9999",
                        clipping_geometry="ClippingGeometry",
                        maintain_clipping_extent="NO_MAINTAIN_EXTENT"
                    )
                    processed += 1
                else:
                    # Tile outside boundary - skip
                    skipped += 1
                    
        except Exception as e:
            print(f"Error processing {tile_file}: {e}")
            skipped += 1
    
    print(f"\n✅ Tile clipping complete!")
    print(f"Processed: {processed} tiles")
    print(f"Skipped: {skipped} tiles (outside boundary)")
    print(f"Output folder: {output_folder}")

# Example usage
if __name__ == "__main__":
    # WATERLOO REGION IMAGERY 2024 SERVICE
    waterloo_service_url = "https://gis.regionofwaterloo.ca/waimagery/rest/services/Imagery_2024/ImageServer"
    
    # Update these paths for your local system
    boundary_output = r"/Users/doraliu/Documents/PartTimeJob/NRSI-GIS/Segment-huge-service-layer-into-tiles/waterloo_imagery_boundary.shp"
    tiles_input = r"/Users/doraliu/Documents/PartTimeJob/NRSI-GIS/Segment-huge-service-layer-into-tiles/tiles"  # Your existing tiles folder
    tiles_output = r"/Users/doraliu/Documents/PartTimeJob/NRSI-GIS/Segment-huge-service-layer-into-tiles/clipped_tiles"
    
    # Option 1: Create boundary from web service (RECOMMENDED)
    print("Creating boundary mask from Waterloo Imagery 2024 service...")
    boundary_shp = create_imagery_boundary_mask(
        input_raster=waterloo_service_url,
        output_shapefile=boundary_output,
        simplify_tolerance=50  # 50m simplification for large dataset
    )
    
    # Option 2: Or use layer name if you've already added the service to ArcGIS Pro
    # boundary_shp = create_imagery_boundary_mask(
    #     input_raster="Imagery_2024",  # Layer name in your project
    #     output_shapefile=boundary_output,
    #     simplify_tolerance=50
    # )
    
    if boundary_shp:
        print(f"\n✅ Boundary created: {boundary_shp}")
        
        # Optional: Clip existing tiles with the boundary (if you have tiles already)
        if os.path.exists(tiles_input):
            print("\nClipping existing tiles with boundary...")
            clip_tiles_with_boundary(
                tiles_folder=tiles_input,
                boundary_shapefile=boundary_shp,
                output_folder=tiles_output
            )
        
        print("\n=== BOUNDARY MASKING COMPLETE ===")
        print(f"Boundary shapefile: {boundary_shp}")
        print("Next steps:")
        print("1. Open the boundary shapefile in ArcGIS Pro to verify")
        print("2. Use this boundary for creating classification sections")
        print("3. Use the boundary to avoid processing blank areas")
    else:
        print("❌ Failed to create boundary mask")
