import arcpy
import os
from datetime import datetime

def create_geographic_sections(imagery_layer, boundary_shapefile, num_sections=6, output_folder=None):
    """
    Divide the imagery into geographic sections for distributed classification
    
    Parameters:
    imagery_layer: Input imagery layer name, web service URL, or file path
    boundary_shapefile: Boundary polygon to constrain sections
    num_sections: Number of sections to create (recommended: 5-6)
    output_folder: Folder to save section extents and metadata
    """
    
    print("=== CREATING GEOGRAPHIC SECTIONS FOR CLASSIFICATION ===")
    print(f"Imagery source: {imagery_layer}")
    print(f"Target sections: {num_sections}")
    
    if output_folder is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_folder = f"classification_sections_{timestamp}"
    
    os.makedirs(output_folder, exist_ok=True)
    
    # Handle different imagery input types
    imagery_ref = None
    
    if isinstance(imagery_layer, str) and imagery_layer.startswith("http"):
        print("Creating temporary layer from web service...")
        temp_layer_name = "Temp_Classification_Service"
        try:
            arcpy.management.MakeImageServerLayer(
                in_image_service=imagery_layer,
                out_imageserver_layer=temp_layer_name
            )
            imagery_ref = temp_layer_name
            print(f"✅ Temporary layer created: {temp_layer_name}")
        except Exception as e:
            print(f"❌ Error creating temporary layer: {e}")
            return None, None, []
    elif os.path.isfile(str(imagery_layer)):
        imagery_ref = imagery_layer
    else:
        # Try to find layer in current project
        project = arcpy.mp.ArcGISProject("CURRENT")
        map_ = project.activeMap or project.listMaps()[0]
        
        for lyr in map_.listLayers():
            if lyr.name == imagery_layer:
                imagery_ref = lyr
                break
        
        if imagery_ref is None:
            print(f"❌ Layer '{imagery_layer}' not found in current project")
            return None, None, []
    
    # Get the boundary extent
    desc = arcpy.Describe(boundary_shapefile)
    extent = desc.extent
    
    # Calculate section layout
    # For 6 sections, use 3x2 grid (3 columns, 2 rows)
    if num_sections <= 4:
        cols, rows = 2, 2
    elif num_sections <= 6:
        cols, rows = 3, 2
    elif num_sections <= 9:
        cols, rows = 3, 3
    else:
        cols, rows = 4, 3
    
    # Adjust to actual number of sections needed
    total_cells = cols * rows
    if total_cells > num_sections:
        # Remove some cells from the grid
        sections_to_create = num_sections
    else:
        sections_to_create = total_cells
    
    print(f"Creating {cols}x{rows} grid ({sections_to_create} sections)")
    
    # Calculate section dimensions
    total_width = extent.XMax - extent.XMin
    total_height = extent.YMax - extent.YMin
    section_width = total_width / cols
    section_height = total_height / rows
    
    print(f"Each section: {section_width/1000:.1f} x {section_height/1000:.1f} km")
    
    # Create section extents
    sections = []
    section_id = 1
    
    for row in range(rows):
        for col in range(cols):
            if section_id > sections_to_create:
                break
                
            # Calculate section bounds
            xmin = extent.XMin + (col * section_width)
            xmax = extent.XMin + ((col + 1) * section_width)
            ymin = extent.YMin + (row * section_height)
            ymax = extent.YMin + ((row + 1) * section_height)
            
            # Create section polygon
            section_poly = arcpy.Polygon(arcpy.Array([
                arcpy.Point(xmin, ymin),
                arcpy.Point(xmax, ymin),
                arcpy.Point(xmax, ymax),
                arcpy.Point(xmin, ymax)
            ]), desc.spatialReference)
            
            # Intersect with boundary to get actual imagery area
            temp_intersect = f"in_memory/section_{section_id}_intersect"
            section_feature = f"in_memory/section_{section_id}_poly"
            
            # Create temporary feature for intersection
            arcpy.management.CreateFeatureclass(
                "in_memory", f"section_{section_id}_poly", 
                "POLYGON", spatial_reference=desc.spatialReference
            )
            
            with arcpy.da.InsertCursor(section_feature, ["SHAPE@"]) as cursor:
                cursor.insertRow([section_poly])
            
            # Intersect with boundary
            arcpy.analysis.Intersect(
                [section_feature, boundary_shapefile],
                temp_intersect
            )
            
            # Get the intersected area
            area_sqkm = 0
            with arcpy.da.SearchCursor(temp_intersect, ["SHAPE@"]) as cursor:
                for row_data in cursor:
                    area_sqkm += row_data[0].area / 1000000
            
            if area_sqkm > 1:  # Only include sections with >1 sq km of imagery
                section_info = {
                    'id': section_id,
                    'extent': [xmin, ymin, xmax, ymax],
                    'area_sqkm': area_sqkm,
                    'grid_position': f"R{row+1}C{col+1}",
                    'poly_feature': temp_intersect
                }
                sections.append(section_info)
                
                print(f"Section {section_id} (R{row+1}C{col+1}): {area_sqkm:.1f} sq km")
            
            section_id += 1
    
    # Create section shapefiles
    print(f"\nCreating {len(sections)} section shapefiles...")
    
    section_shapefile = os.path.join(output_folder, "classification_sections.shp")
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(section_shapefile),
        out_name=os.path.basename(section_shapefile),
        geometry_type="POLYGON",
        spatial_reference=desc.spatialReference
    )
    
    # Add fields
    arcpy.management.AddField(section_shapefile, "Section_ID", "SHORT")
    arcpy.management.AddField(section_shapefile, "Grid_Pos", "TEXT", field_length=10)
    arcpy.management.AddField(section_shapefile, "Area_SqKm", "DOUBLE")
    arcpy.management.AddField(section_shapefile, "Assigned_To", "TEXT", field_length=50)
    arcpy.management.AddField(section_shapefile, "Status", "TEXT", field_length=20)
    
    # Insert section polygons
    with arcpy.da.InsertCursor(section_shapefile, 
                              ["SHAPE@", "Section_ID", "Grid_Pos", "Area_SqKm", "Status"]) as cursor:
        for section in sections:
            with arcpy.da.SearchCursor(section['poly_feature'], ["SHAPE@"]) as shape_cursor:
                for shape_row in shape_cursor:
                    cursor.insertRow([
                        shape_row[0],
                        section['id'],
                        section['grid_position'],
                        section['area_sqkm'],
                        "Pending"
                    ])
    
    # Create metadata file
    metadata_file = os.path.join(output_folder, "sections_metadata.txt")
    with open(metadata_file, 'w') as f:
        f.write("CLASSIFICATION SECTIONS METADATA\n")
        f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total sections: {len(sections)}\n")
        f.write(f"Grid layout: {cols}x{rows}\n\n")
        
        f.write("SECTION DETAILS:\n")
        for section in sections:
            f.write(f"Section {section['id']} ({section['grid_position']}):\n")
            f.write(f"  Area: {section['area_sqkm']:.1f} sq km\n")
            f.write(f"  Extent: {section['extent']}\n")
            f.write(f"  Assignment: [To be assigned]\n\n")
        
        f.write("RECOMMENDED RANDOM POLYGONS PER SECTION:\n")
        for section in sections:
            # Calculate polygons based on area (roughly 1 polygon per 0.5 sq km)
            recommended_polygons = max(50, min(200, int(section['area_sqkm'] * 2)))
            f.write(f"Section {section['id']}: {recommended_polygons} polygons\n")
    
    print(f"\n✅ Geographic sections created!")
    print(f"Section shapefile: {section_shapefile}")
    print(f"Metadata file: {metadata_file}")
    print(f"Output folder: {output_folder}")
    
    return section_shapefile, metadata_file, sections

def export_section_rasters(imagery_layer, sections_shapefile, output_folder, tile_size_mb=500):
    """
    Export each section as a separate raster for individual classification
    """
    print("\n=== EXPORTING SECTION RASTERS ===")
    
    sections_folder = os.path.join(output_folder, "section_rasters")
    os.makedirs(sections_folder, exist_ok=True)
    
    # Handle different imagery input types (same as above)
    imagery_ref = None
    temp_layer_cleanup = None
    
    if isinstance(imagery_layer, str) and imagery_layer.startswith("http"):
        print("Using web service for raster export...")
        temp_layer_name = "Temp_Export_Service"
        try:
            arcpy.management.MakeImageServerLayer(
                in_image_service=imagery_layer,
                out_imageserver_layer=temp_layer_name
            )
            imagery_ref = temp_layer_name
            temp_layer_cleanup = temp_layer_name
        except Exception as e:
            print(f"❌ Error creating temporary layer for export: {e}")
            return None
    elif os.path.isfile(str(imagery_layer)):
        imagery_ref = imagery_layer
    else:
        # Try to find layer in current project
        project = arcpy.mp.ArcGISProject("CURRENT")
        map_ = project.activeMap or project.listMaps()[0]
        
        for lyr in map_.listLayers():
            if lyr.name == imagery_layer:
                imagery_ref = lyr
                break
        
        if imagery_ref is None:
            print(f"❌ Layer '{imagery_layer}' not found for export")
            return None
    
    with arcpy.da.SearchCursor(sections_shapefile, 
                              ["Section_ID", "Grid_Pos", "SHAPE@", "Area_SqKm"]) as cursor:
        for row in cursor:
            section_id, grid_pos, shape, area_sqkm = row
            
            output_raster = os.path.join(sections_folder, f"section_{section_id:02d}_{grid_pos}.tif")
            
            print(f"Exporting Section {section_id} ({grid_pos}): {area_sqkm:.1f} sq km")
            
            try:
                # Clip imagery to section boundary
                arcpy.management.Clip(
                    in_raster=imagery_ref,
                    rectangle="",
                    out_raster=output_raster,
                    in_template_dataset=shape,
                    nodata_value="-9999",
                    clipping_geometry="ClippingGeometry",
                    maintain_clipping_extent="NO_MAINTAIN_EXTENT"
                )
                
                # Check file size
                file_size_mb = os.path.getsize(output_raster) / (1024*1024)
                print(f"  ✅ Exported: {file_size_mb:.0f} MB")
                
                if file_size_mb > tile_size_mb:
                    print(f"  ⚠️  Large file ({file_size_mb:.0f} MB) - consider further subdivision")
                
            except Exception as e:
                print(f"  ❌ Error exporting section {section_id}: {e}")
    
    # Clean up temporary layer if created
    if temp_layer_cleanup:
        try:
            arcpy.management.Delete(temp_layer_cleanup)
            print(f"✅ Cleaned up temporary layer: {temp_layer_cleanup}")
        except:
            pass
    
    print(f"\n✅ Section rasters exported to: {sections_folder}")
    return sections_folder

# Example usage
if __name__ == "__main__":
    # WATERLOO REGION IMAGERY 2024 SERVICE
    waterloo_service_url = "https://gis.regionofwaterloo.ca/waimagery/rest/services/Imagery_2024/ImageServer"
    
    # Update these paths for your local system
    boundary_shp = r"/Users/doraliu/Documents/PartTimeJob/NRSI-GIS/Segment-huge-service-layer-into-tiles/waterloo_imagery_boundary.shp"
    output_dir = r"/Users/doraliu/Documents/PartTimeJob/NRSI-GIS/Segment-huge-service-layer-into-tiles/classification_project"
    
    # Create the boundary first if it doesn't exist
    if not os.path.exists(boundary_shp):
        print("Boundary shapefile not found. Creating it first...")
        print("Please run create_boundary_mask.py first to create the boundary.")
        print(f"Expected boundary file: {boundary_shp}")
        exit(1)
    
    print("=== WATERLOO REGION CLASSIFICATION SECTIONS ===")
    print(f"Using imagery service: {waterloo_service_url}")
    print(f"Using boundary: {boundary_shp}")
    
    # Step 1: Create geographic sections
    sections_shp, metadata_file, section_info = create_geographic_sections(
        imagery_layer=waterloo_service_url,  # Web service URL
        boundary_shapefile=boundary_shp,
        num_sections=6,  # Adjust based on your team size (5-6 recommended)
        output_folder=output_dir
    )
    
    # Step 2: Export section rasters
    if sections_shp:
        print(f"\n✅ Sections created: {sections_shp}")
        
        # Ask user if they want to export rasters (can be large)
        print("\n" + "="*50)
        print("EXPORT SECTION RASTERS?")
        print("This will download and save each section as a separate raster file.")
        print("Each section may be 100-500 MB depending on area and resolution.")
        print("="*50)
        
        response = input("Export section rasters now? (y/n): ").lower().strip()
        
        if response == 'y':
            sections_raster_folder = export_section_rasters(
                imagery_layer=waterloo_service_url,
                sections_shapefile=sections_shp,
                output_folder=output_dir,
                tile_size_mb=800  # Max 800MB per section
            )
            
            print("\n=== SECTION SETUP COMPLETE ===")
            print(f"Section boundaries: {sections_shp}")
            print(f"Section rasters: {sections_raster_folder}")
            print(f"Metadata: {metadata_file}")
        else:
            print("\n=== SECTION BOUNDARIES CREATED ===")
            print(f"Section boundaries: {sections_shp}")
            print(f"Metadata: {metadata_file}")
            print("\nYou can export rasters later by running this script again")
            print("or manually export each section in ArcGIS Pro")
        
        print("\n" + "="*50)
        print("NEXT STEPS:")
        print("1. Open ArcGIS Pro and add the sections shapefile")
        print("2. Add the Waterloo imagery service layer")
        print("3. Review the section boundaries")
        print("4. Assign each section to a team member")
        print("5. Generate training polygons for each section")
        print("6. Perform supervised classification on each section")
        print("7. Combine results using the mosaic combination script")
        print("="*50)
    else:
        print("❌ Failed to create sections")
