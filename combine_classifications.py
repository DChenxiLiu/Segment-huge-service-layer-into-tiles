import arcpy
import os
from datetime import datetime

def combine_section_classifications(classified_sections_folder, output_mosaic, 
                                  boundary_shapefile=None, 
                                  classification_schema=None):
    """
    Combine individual section classifications into a unified mosaic
    
    Parameters:
    classified_sections_folder: Folder containing classified raster sections
    output_mosaic: Output path for combined mosaic (geodatabase)
    boundary_shapefile: Optional boundary to clip final result
    classification_schema: Optional dictionary mapping class values to names
    """
    
    print("=== COMBINING SECTION CLASSIFICATIONS ===")
    print(f"Input folder: {classified_sections_folder}")
    print(f"Output mosaic: {output_mosaic}")
    
    # Get list of classified rasters
    classified_files = []
    for file in os.listdir(classified_sections_folder):
        if file.endswith('.tif') and 'classified' in file.lower():
            classified_files.append(os.path.join(classified_sections_folder, file))
    
    if len(classified_files) == 0:
        print("❌ No classified raster files found!")
        print("Expected files with 'classified' in the filename")
        return None
    
    print(f"Found {len(classified_files)} classified sections:")
    for i, file in enumerate(classified_files[:5]):  # Show first 5
        print(f"  {i+1}. {os.path.basename(file)}")
    if len(classified_files) > 5:
        print(f"  ... and {len(classified_files) - 5} more")
    
    try:
        # Create output geodatabase if it doesn't exist
        output_gdb = os.path.dirname(output_mosaic)
        if not arcpy.Exists(output_gdb):
            print("Creating output geodatabase...")
            arcpy.management.CreateFileGDB(
                out_folder_path=os.path.dirname(output_gdb),
                out_name=os.path.basename(output_gdb)
            )
        
        # Get spatial reference from first raster
        first_raster = classified_files[0]
        desc = arcpy.Describe(first_raster)
        spatial_ref = desc.spatialReference
        
        print(f"Using spatial reference: {spatial_ref.name}")
        
        # Method 1: Create Mosaic Dataset (Recommended for large datasets)
        mosaic_name = os.path.basename(output_mosaic)
        
        # Delete existing mosaic if it exists
        if arcpy.Exists(output_mosaic):
            print("Deleting existing mosaic...")
            arcpy.management.Delete(output_mosaic)
        
        # Create new mosaic dataset
        print("Creating mosaic dataset...")
        arcpy.management.CreateMosaicDataset(
            in_workspace=output_gdb,
            in_mosaicdataset_name=mosaic_name,
            coordinate_system=spatial_ref
        )
        
        # Add rasters to mosaic
        print("Adding classified rasters to mosaic...")
        arcpy.management.AddRastersToMosaicDataset(
            in_mosaic_dataset=output_mosaic,
            raster_type="Raster Dataset",
            input_path=classified_sections_folder,
            update_cellsize_ranges="UPDATE_CELL_SIZES",
            update_boundary="UPDATE_BOUNDARY",
            update_overviews="NO_OVERVIEWS",
            maximum_pyramid_levels="",
            maximum_cell_size="0",
            minimum_dimension="1500",
            spatial_reference="",
            filter="*classified*.tif",  # Only add classified rasters
            sub_folder="SUBFOLDERS",
            duplicate_items_action="ALLOW_DUPLICATES",
            build_pyramids="NO_PYRAMIDS",
            calculate_statistics="NO_STATISTICS",
            build_thumbnails="NO_THUMBNAILS"
        )
        
        # Set mosaic properties for classification data
        print("Configuring mosaic properties...")
        
        # Set blending to handle edge effects
        arcpy.management.SetMosaicDatasetProperties(
            in_mosaic_dataset=output_mosaic,
            rows_maximum_imagesize="4100",
            columns_maximum_imagesize="15000",
            allowed_compressions="None;JPEG;LZ77;LERC",
            default_compression_type="LZ77",
            JPEG_quality="75",
            LERC_Tolerance="0.01",
            resampling_type="NEAREST",  # Important for classification data
            clip_to_footprints="NOT_CLIP",
            footprints_may_contain_nodata="FOOTPRINTS_MAY_CONTAIN_NODATA",
            clip_to_boundary="NOT_CLIP",
            color_correction="NOT_APPLY",
            allowed_mensuration_capabilities="NONE",
            default_mensuration_capabilities="NONE",
            allowed_mosaic_methods="NorthWest;Center;LockRaster;ByAttribute;Nadir;Viewpoint;Seamline;None",
            default_mosaic_method="ByAttribute",
            order_field="",
            order_base=""
        )
        
        # Handle overlapping areas (use mode or first for classification data)
        arcpy.management.SetMosaicDatasetProperties(
            in_mosaic_dataset=output_mosaic,
            default_mosaic_method="Center",
            order_field="",
            ascending="ASC",
            mosaic_operator="FIRST"  # Use first value for overlaps
        )
        
        # Build overviews for performance
        print("Building overviews...")
        arcpy.management.BuildOverviews(
            in_mosaic_dataset=output_mosaic,
            where_clause="",
            define_missing_tiles="DEFINE_MISSING_TILES",
            generate_overviews="GENERATE_OVERVIEWS",
            generate_missing_images="GENERATE_MISSING_IMAGES",
            regenerate_stale_images="REGENERATE_STALE_IMAGES"
        )
        
        # Method 2: Create single raster output (Alternative)
        single_raster_output = output_mosaic.replace(".gdb/", ".gdb/") + "_single"
        
        print("Creating single combined raster...")
        env_workspace = arcpy.env.workspace
        arcpy.env.workspace = output_gdb
        
        # Use Cell Statistics to combine overlapping areas
        if len(classified_files) > 1:
            # For overlapping areas, use majority/mode
            arcpy.gp.CellStatistics_sa(
                in_rasters_or_constants=";".join(classified_files),
                out_raster=single_raster_output,
                statistics_type="MAJORITY",
                ignore_nodata="DATA"
            )
        else:
            # Single raster, just copy
            arcpy.management.CopyRaster(
                in_raster=classified_files[0],
                out_rasterdataset=single_raster_output
            )
        
        arcpy.env.workspace = env_workspace
        
        # Apply boundary mask if provided
        if boundary_shapefile and arcpy.Exists(boundary_shapefile):
            print("Applying boundary mask...")
            
            masked_output = output_mosaic + "_masked"
            
            # Clip to boundary
            arcpy.management.Clip(
                in_raster=single_raster_output,
                rectangle="",
                out_raster=masked_output,
                in_template_dataset=boundary_shapefile,
                nodata_value="-9999",
                clipping_geometry="ClippingGeometry",
                maintain_clipping_extent="NO_MAINTAIN_EXTENT"
            )
            
            print(f"✅ Masked result: {masked_output}")
        
        # Create classification report
        create_classification_report(output_mosaic, classified_files, classification_schema)
        
        print(f"✅ Classification combination complete!")
        print(f"Mosaic dataset: {output_mosaic}")
        print(f"Single raster: {single_raster_output}")
        
        return output_mosaic
        
    except Exception as e:
        print(f"❌ Error combining classifications: {e}")
        return None

def create_classification_report(mosaic_dataset, input_files, classification_schema=None):
    """Create a report summarizing the combined classification"""
    
    output_folder = os.path.dirname(os.path.dirname(mosaic_dataset))
    report_file = os.path.join(output_folder, "classification_combination_report.txt")
    
    print("Creating classification report...")
    
    with open(report_file, 'w') as f:
        f.write("CLASSIFICATION COMBINATION REPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"Combined mosaic: {mosaic_dataset}\n")
        f.write(f"Number of input sections: {len(input_files)}\n\n")
        
        f.write("INPUT SECTIONS:\n")
        for i, file in enumerate(input_files):
            f.write(f"{i+1:2d}. {os.path.basename(file)}\n")
            
            # Get file size
            try:
                size_mb = os.path.getsize(file) / (1024*1024)
                f.write(f"     Size: {size_mb:.1f} MB\n")
            except:
                pass
        
        f.write(f"\nTOTAL INPUT SIZE: ")
        total_size = sum(os.path.getsize(f) for f in input_files if os.path.exists(f))
        f.write(f"{total_size / (1024**3):.1f} GB\n\n")
        
        # Classification schema if provided
        if classification_schema:
            f.write("CLASSIFICATION SCHEMA:\n")
            for value, name in classification_schema.items():
                f.write(f"  {value}: {name}\n")
            f.write("\n")
        
        f.write("QUALITY CONTROL CHECKLIST:\n")
        f.write("□ Visual inspection of mosaic boundaries\n")
        f.write("□ Check for seamless transitions between sections\n")
        f.write("□ Verify classification consistency across boundaries\n")
        f.write("□ Validate against ground truth data\n")
        f.write("□ Calculate accuracy statistics\n")
        f.write("□ Generate final area statistics by class\n\n")
        
        f.write("NEXT STEPS:\n")
        f.write("1. Open combined mosaic in ArcGIS Pro\n")
        f.write("2. Review for edge effects and inconsistencies\n")
        f.write("3. Perform accuracy assessment\n")
        f.write("4. Calculate final area statistics\n")
        f.write("5. Export final products (maps, statistics, metadata)\n")
    
    print(f"✅ Report saved: {report_file}")

def validate_section_compatibility(classified_sections_folder):
    """
    Validate that all classified sections are compatible for combination
    """
    print("=== VALIDATING SECTION COMPATIBILITY ===")
    
    classified_files = []
    for file in os.listdir(classified_sections_folder):
        if file.endswith('.tif') and 'classified' in file.lower():
            classified_files.append(os.path.join(classified_sections_folder, file))
    
    if len(classified_files) < 2:
        print("⚠️  Only one classified section found - no combination needed")
        return True
    
    # Check spatial reference
    spatial_refs = []
    cell_sizes = []
    class_ranges = []
    
    for file in classified_files:
        try:
            desc = arcpy.Describe(file)
            spatial_refs.append(desc.spatialReference.name)
            
            raster = arcpy.Raster(file)
            cell_sizes.append((raster.meanCellWidth, raster.meanCellHeight))
            
            # Get class value range
            min_val = raster.minimum
            max_val = raster.maximum
            class_ranges.append((min_val, max_val))
            
        except Exception as e:
            print(f"⚠️  Error checking {file}: {e}")
    
    # Validate spatial references match
    unique_srs = set(spatial_refs)
    if len(unique_srs) > 1:
        print("❌ ISSUE: Multiple spatial reference systems found:")
        for srs in unique_srs:
            print(f"  - {srs}")
        print("All sections must have the same spatial reference!")
        return False
    
    # Validate cell sizes are similar
    unique_cell_sizes = set(cell_sizes)
    if len(unique_cell_sizes) > 1:
        print("⚠️  WARNING: Different cell sizes found:")
        for size in unique_cell_sizes:
            print(f"  - {size[0]:.3f} x {size[1]:.3f}")
        print("Consider resampling to common resolution")
    
    # Check class value ranges
    all_min = min(r[0] for r in class_ranges)
    all_max = max(r[1] for r in class_ranges)
    
    print(f"✅ Spatial reference: {spatial_refs[0]}")
    print(f"✅ Classification value range: {all_min} to {all_max}")
    print(f"✅ {len(classified_files)} sections ready for combination")
    
    return True

# Example usage
if __name__ == "__main__":
    # Update these paths
    classified_folder = r"C:\path\to\classified_sections"  # Folder with classified rasters
    output_gdb = r"C:\path\to\final_classification.gdb"   # Output geodatabase
    mosaic_name = "Combined_Classification"
    boundary_shp = r"C:\path\to\imagery_boundary.shp"     # Optional boundary
    
    # Define your classification schema (optional)
    classification_classes = {
        1: "Water",
        2: "Urban/Built",
        3: "Forest",
        4: "Agriculture",
        5: "Grassland",
        6: "Bare Ground"
    }
    
    # Validate compatibility first
    if validate_section_compatibility(classified_folder):
        
        # Combine classifications
        combined_mosaic = combine_section_classifications(
            classified_sections_folder=classified_folder,
            output_mosaic=os.path.join(output_gdb, mosaic_name),
            boundary_shapefile=boundary_shp,
            classification_schema=classification_classes
        )
        
        if combined_mosaic:
            print("\n=== CLASSIFICATION COMBINATION COMPLETE ===")
            print(f"Final mosaic: {combined_mosaic}")
            print("\nRECOMMENDED QUALITY CONTROL:")
            print("1. Visual inspection for edge effects")
            print("2. Accuracy assessment with validation data")
            print("3. Area calculation by land cover class")
            print("4. Comparison with reference datasets")
    else:
        print("❌ Section compatibility issues must be resolved first")
