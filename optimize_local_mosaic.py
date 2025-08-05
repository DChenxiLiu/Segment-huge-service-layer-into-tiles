"""
LOCAL MOSAIC OPTIMIZATION SCRIPT
=================================

This script provides optimized handling for local mosaic datasets, 
particularly useful for the 2025 Waterloo imagery if downloaded locally.

Features:
- Optimized processing for large local mosaics (1TB+)
- Smart boundary detection from actual data coverage
- Efficient section extraction
- Memory-optimized workflows
"""

import arcpy
import os
import time
from datetime import datetime

def analyze_local_mosaic(mosaic_path, sample_percentage=5):
    """
    Analyze a local mosaic dataset to understand its properties and data coverage
    
    Parameters:
    mosaic_path: Path to the local mosaic dataset
    sample_percentage: Percentage of area to sample for analysis
    """
    
    print("=== ANALYZING LOCAL MOSAIC DATASET ===")
    print(f"Mosaic: {mosaic_path}")
    
    try:
        # Get basic properties
        desc = arcpy.Describe(mosaic_path)
        extent = desc.extent
        spatial_ref = desc.spatialReference
        
        print(f"✅ Mosaic found and accessible")
        print(f"Spatial Reference: {spatial_ref.name}")
        print(f"Full Extent: {extent.XMin:.0f}, {extent.YMin:.0f}, {extent.XMax:.0f}, {extent.YMax:.0f}")
        
        # Calculate total area
        total_area_sqkm = ((extent.XMax - extent.XMin) * (extent.YMax - extent.YMin)) / 1000000
        print(f"Total Extent Area: {total_area_sqkm:.1f} sq km")
        
        # Get raster properties if it's a raster
        try:
            raster_obj = arcpy.Raster(mosaic_path)
            print(f"Cell Size: {raster_obj.meanCellWidth:.2f} x {raster_obj.meanCellHeight:.2f} meters")
            print(f"Dimensions: {raster_obj.width} x {raster_obj.height} pixels")
            
            # Estimate file size
            estimated_size_gb = (raster_obj.width * raster_obj.height * 3 * 1) / (1024**3)  # Rough estimate
            print(f"Estimated Size: {estimated_size_gb:.1f} GB")
            
        except:
            print("Mosaic dataset properties (not single raster)")
        
        # Check if it's a mosaic dataset
        if desc.dataType == "MosaicDataset":
            print("✅ Detected as Mosaic Dataset")
            
            # Count rasters in mosaic
            with arcpy.da.SearchCursor(mosaic_path, ["OBJECTID"]) as cursor:
                raster_count = sum(1 for row in cursor)
            print(f"Contains {raster_count} raster items")
            
            # Get overview information
            has_overviews = desc.hasOverviews if hasattr(desc, 'hasOverviews') else "Unknown"
            print(f"Has Overviews: {has_overviews}")
        
        # Sample data coverage (check for NoData areas)
        print(f"\nSampling {sample_percentage}% of area for data coverage analysis...")
        data_coverage_ratio = estimate_data_coverage(mosaic_path, extent, sample_percentage)
        
        print(f"Estimated Data Coverage: {data_coverage_ratio*100:.1f}%")
        
        if data_coverage_ratio < 0.7:
            print("⚠️  Significant NoData areas detected - boundary masking recommended")
        else:
            print("✅ Good data coverage across extent")
        
        return {
            'path': mosaic_path,
            'extent': extent,
            'spatial_ref': spatial_ref,
            'total_area_sqkm': total_area_sqkm,
            'data_coverage': data_coverage_ratio,
            'is_mosaic_dataset': desc.dataType == "MosaicDataset"
        }
        
    except Exception as e:
        print(f"❌ Error analyzing mosaic: {e}")
        return None

def estimate_data_coverage(mosaic_path, extent, sample_percentage=5):
    """
    Estimate what percentage of the mosaic contains actual data (not NoData)
    """
    try:
        # Create sample points across the extent
        sample_points = create_sample_grid(extent, sample_percentage)
        
        data_points = 0
        total_points = len(sample_points)
        
        print(f"Testing {total_points} sample points...")
        
        for i, (x, y) in enumerate(sample_points):
            if i % 100 == 0 and i > 0:
                print(f"  Processed {i}/{total_points} points...")
            
            try:
                result = arcpy.management.GetCellValue(mosaic_path, f"{x} {y}")
                cell_value = result.getOutput(0)
                
                if cell_value != "NoData" and cell_value != "":
                    data_points += 1
            except:
                # If we can't get cell value, assume NoData
                pass
        
        coverage_ratio = data_points / total_points if total_points > 0 else 0
        return coverage_ratio
        
    except Exception as e:
        print(f"Warning: Could not estimate data coverage: {e}")
        return 0.8  # Conservative estimate

def create_sample_grid(extent, sample_percentage):
    """Create a grid of sample points for coverage analysis"""
    
    # Calculate number of points based on percentage
    total_area = (extent.XMax - extent.XMin) * (extent.YMax - extent.YMin)
    target_points = int((total_area / 1000000) * sample_percentage)  # Points per sq km
    target_points = max(100, min(1000, target_points))  # Bounds: 100-1000 points
    
    # Create grid
    points_per_side = int(target_points ** 0.5)
    
    x_step = (extent.XMax - extent.XMin) / points_per_side
    y_step = (extent.YMax - extent.YMin) / points_per_side
    
    sample_points = []
    for i in range(points_per_side):
        for j in range(points_per_side):
            x = extent.XMin + (i + 0.5) * x_step
            y = extent.YMin + (j + 0.5) * y_step
            sample_points.append((x, y))
    
    return sample_points

def create_optimized_boundary_from_mosaic(mosaic_path, output_shapefile, 
                                        data_threshold=0.5, simplify_tolerance=100):
    """
    Create an optimized boundary that excludes NoData areas from a local mosaic
    
    Parameters:
    mosaic_path: Path to local mosaic
    output_shapefile: Output boundary shapefile
    data_threshold: Minimum data coverage required (0.0-1.0)
    simplify_tolerance: Simplification tolerance in meters
    """
    
    print("=== CREATING OPTIMIZED BOUNDARY FROM LOCAL MOSAIC ===")
    
    try:
        # Method 1: Try to extract footprint if it's a mosaic dataset
        desc = arcpy.Describe(mosaic_path)
        
        if desc.dataType == "MosaicDataset":
            print("Using mosaic dataset footprint method...")
            
            # Extract the boundary from mosaic dataset
            temp_boundary = "in_memory/mosaic_boundary"
            
            # Get the boundary of the mosaic dataset
            arcpy.management.ExportMosaicDatasetGeometry(
                in_mosaic_dataset=mosaic_path,
                out_featureclass=temp_boundary,
                geometry_type="FOOTPRINT"
            )
            
            # Dissolve all footprints into single boundary
            temp_dissolved = "in_memory/dissolved_boundary"
            arcpy.management.Dissolve(
                in_features=temp_boundary,
                out_feature_class=temp_dissolved
            )
            
            # Simplify the boundary
            arcpy.cartography.SimplifyPolygon(
                in_features=temp_dissolved,
                out_feature_class=output_shapefile,
                algorithm="POINT_REMOVE",
                tolerance=f"{simplify_tolerance} Meters",
                minimum_area="1000 SquareMeters",
                error_option="RESOLVE_ERRORS",
                collapsed_point_option="NO_KEEP"
            )
            
        else:
            # Method 2: For regular rasters, use raster-to-polygon conversion
            print("Using raster-to-polygon method...")
            
            # Create binary mask of data areas
            temp_binary = "in_memory/data_mask"
            
            # Use conditional statement to identify data areas
            arcpy.gp.Con_sa(mosaic_path, "1", temp_binary, "", "VALUE >= 0")
            
            # Convert to polygon
            temp_poly = "in_memory/data_polygons"
            arcpy.conversion.RasterToPolygon(
                in_raster=temp_binary,
                out_polygon_features=temp_poly,
                simplify="SIMPLIFY",
                raster_field="VALUE"
            )
            
            # Dissolve and simplify
            temp_dissolved = "in_memory/dissolved_data"
            arcpy.management.Dissolve(
                in_features=temp_poly,
                out_feature_class=temp_dissolved,
                dissolve_field="gridcode"
            )
            
            arcpy.cartography.SimplifyPolygon(
                in_features=temp_dissolved,
                out_feature_class=output_shapefile,
                algorithm="POINT_REMOVE",
                tolerance=f"{simplify_tolerance} Meters",
                minimum_area="10000 SquareMeters",  # 1 hectare minimum
                error_option="RESOLVE_ERRORS",
                collapsed_point_option="NO_KEEP"
            )
        
        # Add attributes
        arcpy.management.AddField(output_shapefile, "Area_SqKm", "DOUBLE")
        arcpy.management.AddField(output_shapefile, "Perimeter_Km", "DOUBLE")
        arcpy.management.AddField(output_shapefile, "Source_Type", "TEXT", field_length=50)
        arcpy.management.AddField(output_shapefile, "Created_Date", "DATE")
        
        # Calculate attributes
        with arcpy.da.UpdateCursor(output_shapefile, 
                                  ["SHAPE@", "Area_SqKm", "Perimeter_Km", "Source_Type", "Created_Date"]) as cursor:
            for row in cursor:
                shape = row[0]
                area_sqm = shape.area
                perimeter_m = shape.length
                
                row[1] = area_sqm / 1000000  # Convert to sq km
                row[2] = perimeter_m / 1000   # Convert to km
                row[3] = "Local Mosaic Dataset"
                row[4] = arcpy.time.ParseDateTimeString("today")
                cursor.updateRow(row)
        
        print("✅ Optimized boundary created successfully!")
        
        # Get final statistics
        with arcpy.da.SearchCursor(output_shapefile, ["Area_SqKm", "Perimeter_Km"]) as cursor:
            for row in cursor:
                print(f"Data Area: {row[0]:.1f} sq km")
                print(f"Perimeter: {row[1]:.1f} km")
        
        return output_shapefile
        
    except Exception as e:
        print(f"❌ Error creating optimized boundary: {e}")
        return None

def optimize_mosaic_for_classification(mosaic_path, output_folder, 
                                     target_section_size_gb=0.5, num_sections=6):
    """
    Optimize a local mosaic for classification by creating manageable sections
    
    Parameters:
    mosaic_path: Path to local mosaic
    output_folder: Folder for optimized outputs
    target_section_size_gb: Target size for each section in GB
    num_sections: Number of sections to create
    """
    
    print("=== OPTIMIZING LOCAL MOSAIC FOR CLASSIFICATION ===")
    
    os.makedirs(output_folder, exist_ok=True)
    
    # First analyze the mosaic
    analysis = analyze_local_mosaic(mosaic_path)
    if not analysis:
        return None
    
    # Create optimized boundary
    boundary_file = os.path.join(output_folder, "optimized_boundary.shp")
    boundary_shp = create_optimized_boundary_from_mosaic(
        mosaic_path=mosaic_path,
        output_shapefile=boundary_file,
        simplify_tolerance=50
    )
    
    if not boundary_shp:
        print("❌ Failed to create boundary")
        return None
    
    # Import the section creation function
    try:
        from create_classification_sections import create_geographic_sections
        
        # Create sections using the local mosaic
        sections_shp, metadata_file, section_info = create_geographic_sections(
            imagery_layer=mosaic_path,
            boundary_shapefile=boundary_shp,
            num_sections=num_sections,
            output_folder=output_folder
        )
        
        if sections_shp:
            print(f"✅ Sections created: {sections_shp}")
            
            # Create summary report
            summary_file = os.path.join(output_folder, "mosaic_optimization_summary.txt")
            with open(summary_file, 'w') as f:
                f.write("LOCAL MOSAIC OPTIMIZATION SUMMARY\n")
                f.write("="*40 + "\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Source Mosaic: {mosaic_path}\n")
                f.write(f"Total Area: {analysis['total_area_sqkm']:.1f} sq km\n")
                f.write(f"Data Coverage: {analysis['data_coverage']*100:.1f}%\n")
                f.write(f"Sections Created: {num_sections}\n\n")
                
                f.write("FILES CREATED:\n")
                f.write(f"- Optimized boundary: {boundary_shp}\n")
                f.write(f"- Section boundaries: {sections_shp}\n")
                f.write(f"- Metadata: {metadata_file}\n\n")
                
                f.write("ADVANTAGES OF LOCAL MOSAIC:\n")
                f.write("- Faster processing (no web service limits)\n")
                f.write("- Full resolution access\n")
                f.write("- Offline capability\n")
                f.write("- Better control over data quality\n\n")
                
                f.write("NEXT STEPS:\n")
                f.write("1. Use sections for distributed classification\n")
                f.write("2. Each team member works on assigned sections\n")
                f.write("3. Combine results when complete\n")
            
            return {
                'boundary': boundary_shp,
                'sections': sections_shp,
                'metadata': metadata_file,
                'summary': summary_file,
                'analysis': analysis
            }
        
    except ImportError:
        print("❌ Could not import section creation functions")
        print("Make sure create_classification_sections.py is available")
        return None

# Example usage
if __name__ == "__main__":
    print("LOCAL MOSAIC OPTIMIZATION FOR WATERLOO 2025 IMAGERY")
    print("="*55)
    
    # Get mosaic path from user
    print("\n📁 MOSAIC DATASET LOCATION")
    print("Please provide the path to your 2025 Waterloo mosaic:")
    print("Examples:")
    print("  - /path/to/Waterloo_2025.gdb/Imagery_Mosaic")
    print("  - /path/to/waterloo_2025_mosaic.tif")
    print("  - C:\\Data\\Waterloo_2025.gdb\\Mosaic_Dataset")
    
    mosaic_path = input("\nEnter mosaic path: ").strip().strip('"\'')
    
    if not (os.path.exists(mosaic_path) or arcpy.Exists(mosaic_path)):
        print(f"❌ Mosaic not found: {mosaic_path}")
        exit(1)
    
    # Get output folder
    output_folder = input("Enter output folder (or press Enter for current directory): ").strip()
    if not output_folder:
        output_folder = os.path.join(os.path.dirname(__file__), "mosaic_optimization")
    
    # Get number of sections
    try:
        num_sections = int(input("Number of sections for team (4-8 recommended): "))
        num_sections = max(2, min(10, num_sections))
    except:
        num_sections = 6
    
    print(f"\n🚀 Starting optimization...")
    print(f"Mosaic: {mosaic_path}")
    print(f"Output: {output_folder}")
    print(f"Sections: {num_sections}")
    
    # Run optimization
    results = optimize_mosaic_for_classification(
        mosaic_path=mosaic_path,
        output_folder=output_folder,
        num_sections=num_sections
    )
    
    if results:
        print("\n" + "="*50)
        print("🎉 MOSAIC OPTIMIZATION COMPLETE!")
        print("="*50)
        print(f"📁 Output folder: {output_folder}")
        print(f"📋 Summary: {results['summary']}")
        print("\n📌 NEXT STEPS:")
        print("1. Open ArcGIS Pro")
        print("2. Add your local mosaic dataset")
        print("3. Add the section boundaries shapefile")
        print("4. Begin distributed classification workflow")
        print("="*50)
    else:
        print("❌ Optimization failed")
