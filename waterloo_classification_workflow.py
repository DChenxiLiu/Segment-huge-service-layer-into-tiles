"""
WATERLOO REGION 2025 IMAGERY CLASSIFICATION WORKFLOW
====================================================

This script provides a complete workflow for processing 2025 Waterloo Region 
imagery for supervised classification using the distributed approach with 
multiple team members.

Supports two input methods:
- 2025 Web Service URL (if available)
- Local 2025 Mosaic File/Geodatabase
"""

import arcpy
import os
import sys
from datetime import datetime

# Add the current directory to Python path to import our custom modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import our custom functions
try:
    from create_boundary_mask import create_imagery_boundary_mask
    from create_classification_sections import create_geographic_sections, export_section_rasters
    from generate_training_polygons_optimized import generate_stratified_polygons, process_all_sections
except ImportError as e:
    print(f"❌ Error importing custom modules: {e}")
    print("Make sure all required .py files are in the same folder:")
    print("- create_boundary_mask.py")
    print("- create_classification_sections.py") 
    print("- generate_training_polygons_optimized.py")
    exit(1)

# Configuration
PROJECT_NAME = "Waterloo_2025_Classification_Project"

# Data source options
DATA_SOURCES = {
    "1": {
        "name": "2025 Web Service",
        "source": None,  # Will be set by user
        "type": "web_service",
        "year": "2025",
        "description": "2025 imagery from Waterloo Region web service"
    },
    "2": {
        "name": "Local 2025 Mosaic",
        "source": None,  # Will be set by user
        "type": "local_mosaic", 
        "year": "2025",
        "description": "Local 2025 imagery mosaic dataset"
    }
}

def setup_project_structure(base_folder):
    """Create the project folder structure"""
    project_folder = os.path.join(base_folder, PROJECT_NAME)
    
    folders = [
        "boundaries",
        "sections", 
        "training_data",
        "classified_results",
        "final_outputs",
        "documentation"
    ]
    
    os.makedirs(project_folder, exist_ok=True)
    
    for folder in folders:
        os.makedirs(os.path.join(project_folder, folder), exist_ok=True)
    
    print(f"✅ Project structure created: {project_folder}")
    return project_folder

def select_data_source():
    """Let user select which data source to use"""
    print("\n📡 DATA SOURCE SELECTION")
    print("="*40)
    print("Choose your 2025 imagery data source:")
    
    for key, source in DATA_SOURCES.items():
        print(f"{key}. {source['name']}")
        print(f"   {source['description']}")
    
    while True:
        choice = input("\nSelect data source (1-2): ").strip()
        if choice in DATA_SOURCES:
            break
        print("Invalid choice. Please enter 1 or 2.")
    
    selected_source = DATA_SOURCES[choice].copy()
    
    # Get additional info for specific source types
    if selected_source["type"] == "web_service":
        print("\n🌐 WEB SERVICE SETUP")
        print("Please provide the 2025 web service URL:")
        print("Example: https://gis.regionofwaterloo.ca/waimagery/rest/services/Imagery_2025/ImageServer")
        
        while True:
            service_url = input("Enter web service URL: ").strip()
            if service_url.startswith("http"):
                selected_source["source"] = service_url
                break
            else:
                print("❌ Please enter a valid URL starting with http or https")
                retry = input("Try again? (y/n): ").lower().strip()
                if retry != 'y':
                    return None
    
    elif selected_source["type"] == "local_mosaic":
        print("\n📁 LOCAL MOSAIC SETUP")
        print("Please provide the path to your 2025 mosaic dataset:")
        print("Examples:")
        print("  - /path/to/Waterloo_2025.gdb/Mosaic_Dataset")
        print("  - /path/to/waterloo_2025_mosaic.tif")
        print("  - C:\\Data\\Waterloo_2025.gdb\\Imagery_Mosaic")
        
        while True:
            mosaic_path = input("Enter mosaic path: ").strip().strip('"\'')
            if os.path.exists(mosaic_path) or arcpy.Exists(mosaic_path):
                selected_source["source"] = mosaic_path
                break
            else:
                print(f"❌ Path not found: {mosaic_path}")
                retry = input("Try again? (y/n): ").lower().strip()
                if retry != 'y':
                    return None
    
    print(f"\n✅ Selected: {selected_source['name']}")
    print(f"📍 Source: {selected_source['source']}")
    
    return selected_source

def main_workflow():
    """Main workflow for Waterloo Region 2025 imagery classification"""
    
    print("="*60)
    print("WATERLOO REGION 2025 IMAGERY CLASSIFICATION WORKFLOW")
    print("="*60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Select data source first
    selected_source = select_data_source()
    if not selected_source:
        print("❌ No valid data source selected. Exiting.")
        return
    
    imagery_source = selected_source["source"]
    source_name = selected_source["name"]
    source_year = selected_source["year"]
    
    print(f"\n✅ Using: {source_name}")
    print(f"📅 Year: {source_year}")
    
    # Get base folder from user
    print("\n📁 PROJECT SETUP")
    base_folder = input("Enter the base folder for your project (or press Enter for current directory): ").strip()
    
    if not base_folder:
        base_folder = os.path.dirname(os.path.abspath(__file__))
    
    if not os.path.exists(base_folder):
        print(f"❌ Folder does not exist: {base_folder}")
        return
    
    # Setup project structure
    project_folder = setup_project_structure(base_folder)
    
    # Define file paths with year in filename
    boundary_file = os.path.join(project_folder, "boundaries", f"waterloo_{source_year.lower()}_boundary.shp")
    sections_folder = os.path.join(project_folder, "sections")
    
    print(f"\n📍 Project folder: {project_folder}")
    print(f"📍 Boundary file: {boundary_file}")
    
    # Step 1: Create boundary mask (Required)
    print("\n" + "="*40)
    print("STEP 1: CREATE BOUNDARY MASK")
    print("="*40)
    print("Creating boundary mask to exclude NoData/blank areas...")
    print("This optimizes processing by focusing only on actual imagery coverage.")
    
    if os.path.exists(boundary_file):
        print(f"✅ Boundary file already exists: {boundary_file}")
        use_existing = input("Use existing boundary? (y/n): ").lower().strip()
        if use_existing != 'y':
            boundary_file = None
    
    if not os.path.exists(boundary_file):
        print(f"Creating boundary mask from {source_name}...")
        boundary_file = create_imagery_boundary_mask(
            input_raster=imagery_source,
            output_shapefile=boundary_file,
            simplify_tolerance=50  # 50m simplification
        )
        
        if not boundary_file:
            print("❌ Failed to create boundary mask")
            return
    
    print(f"✅ Boundary ready: {boundary_file}")
    print("✅ Blank areas will be excluded from processing")
    
    # Step 2: Create classification sections
    print("\n" + "="*40)
    print("STEP 2: CREATE CLASSIFICATION SECTIONS")
    print("="*40)
    
    # Get number of team members
    while True:
        try:
            num_people = int(input("How many team members will work on classification? (recommended: 4-6): "))
            if 2 <= num_people <= 10:
                break
            else:
                print("Please enter a number between 2 and 10")
        except ValueError:
            print("Please enter a valid number")
    
    print(f"Creating {num_people} sections for distributed classification...")
    
    sections_shp, metadata_file, section_info = create_geographic_sections(
        imagery_layer=imagery_source,
        boundary_shapefile=boundary_file,
        num_sections=num_people,
        output_folder=sections_folder
    )
    
    if not sections_shp:
        print("❌ Failed to create sections")
        return
    
    print(f"✅ Sections created: {sections_shp}")
    print(f"📄 Metadata: {metadata_file}")
    
    # Step 3: Generate Training Polygons
    print("\n" + "="*40)
    print("STEP 3: GENERATE TRAINING POLYGONS")
    print("="*40)
    print("Generating training polygons for supervised classification...")
    print("This creates systematic sampling points for each team member's section.")
    
    # Create training data folder
    training_folder = os.path.join(project_folder, "training_data")
    os.makedirs(training_folder, exist_ok=True)
    
    # Get polygon size preference
    print("\nTraining polygon options:")
    print("1. Small (5m hexagons) - For detailed classification")
    print("2. Medium (10m hexagons) - Balanced approach") 
    print("3. Large (15m hexagons) - For broad classification")
    
    while True:
        size_choice = input("Select polygon size (1-3): ").strip()
        if size_choice == "1":
            polygon_size = 5
            break
        elif size_choice == "2":
            polygon_size = 10
            break
        elif size_choice == "3":
            polygon_size = 15
            break
        else:
            print("Please enter 1, 2, or 3")
    
    # Generate polygons for all sections
    print(f"Generating {polygon_size}m hexagonal training polygons for each section...")
    
    training_results = process_all_sections(
        sections_shapefile=sections_shp,
        imagery_source=imagery_source,
        output_folder=training_folder,
        polygon_size=polygon_size,
        min_polygons=150,  # Minimum per section
        max_polygons=300   # Maximum per section
    )
    
    if training_results:
        print("✅ Training polygons generated successfully!")
        print(f"📁 Training data folder: {training_folder}")
        
        # Show summary
        total_polygons = 0
        for section_file in training_results:
            if os.path.exists(section_file):
                with arcpy.da.SearchCursor(section_file, ["OID@"]) as cursor:
                    count = len(list(cursor))
                    total_polygons += count
                    section_name = os.path.basename(section_file).replace('.shp', '')
                    print(f"  {section_name}: {count} polygons")
        
        print(f"📊 Total training polygons: {total_polygons}")
    else:
        print("⚠️ Training polygon generation failed, but workflow can continue")
        print("Team members can create training polygons manually")
    
    # Step 4: Export section rasters (optional)
    print("\n" + "="*40)
    print("STEP 4: EXPORT SECTION RASTERS (OPTIONAL)")
    print("="*40)
    print("This will download raster data for each section.")
    print("Each section may be 100-500 MB depending on size and resolution.")
    
    if selected_source["type"] == "web_service":
        print("Working with web service - you can skip this and work directly in ArcGIS Pro.")
    elif selected_source["type"] == "local_mosaic":
        print("Working with local mosaic - export will create clipped sections.")
    
    export_rasters = input("Export section rasters now? (y/n): ").lower().strip()
    
    if export_rasters == 'y':
        print("Exporting section rasters...")
        raster_folder = export_section_rasters(
            imagery_layer=imagery_source,
            sections_shapefile=sections_shp,
            output_folder=sections_folder,
            tile_size_mb=800  # Max 800MB per section
        )
        
        if raster_folder:
            print(f"✅ Section rasters exported: {raster_folder}")
        else:
            print("⚠️  Raster export failed, but you can still work with the web service")
    
    # Step 5: Generate project summary
    print("\n" + "="*40)
    print("STEP 5: PROJECT SUMMARY")
    print("="*40)
    
    summary_file = os.path.join(project_folder, "documentation", "project_summary.txt")
    
    with open(summary_file, 'w') as f:
        f.write("WATERLOO REGION IMAGERY CLASSIFICATION PROJECT\n")
        f.write("="*50 + "\n")
        f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Data Source: {source_name} ({source_year})\n")
        f.write(f"Source Path: {imagery_source}\n")
        f.write(f"Project folder: {project_folder}\n\n")
        
        f.write("FILES CREATED:\n")
        f.write(f"- Boundary shapefile: {boundary_file}\n")
        f.write(f"- Section boundaries: {sections_shp}\n")
        f.write(f"- Metadata: {metadata_file}\n")
        if 'training_results' in locals() and training_results:
            f.write(f"- Training polygons: {training_folder}\n")
        f.write("\n")
        
        f.write(f"TEAM ASSIGNMENT ({num_people} sections):\n")
        for i in range(num_people):
            f.write(f"Section {i+1}: [Assign to team member]\n")
        
        f.write("\nNEXT STEPS:\n")
        f.write("1. Open ArcGIS Pro and create a new project\n")
        
        if selected_source["type"] == "web_service":
            f.write("2. Add the imagery web service layer\n")
        elif selected_source["type"] == "local_mosaic":
            f.write("2. Add the local mosaic dataset\n")
        else:
            f.write("2. Ensure imagery layer is available in project\n")
            
        f.write("3. Add the section boundaries shapefile\n")
        f.write("4. Add training polygon shapefiles for each section\n")
        f.write("5. Assign each section to a team member\n")
        
        if 'training_results' in locals() and training_results:
            f.write("6. Team members label/edit their training polygons\n")
            f.write("7. Perform supervised classification on each section\n")
            f.write("8. Combine results using mosaic tools\n\n")
            
            f.write("TRAINING DATA STATUS:\n")
            f.write(f"✅ Training polygons automatically generated\n")
            f.write(f"- Polygon size: {polygon_size}m hexagons\n")
            f.write(f"- Location: {training_folder}\n")
            f.write("- Ready for labeling by team members\n\n")
        else:
            f.write("6. Each person creates training polygons for their section\n")
            f.write("7. Perform supervised classification on each section\n")
            f.write("8. Combine results using mosaic tools\n\n")
            
            f.write("TRAINING DATA RECOMMENDATIONS:\n")
            f.write("- 150-300 training polygons per section\n")
            f.write("- 5-6 land cover classes recommended\n")
            f.write("- Use hexagonal polygons (5-15m)\n")
            f.write("- Mix of systematic and random sampling\n\n")
        
        f.write("CONTACT: [Add your contact information]\n")
    
    print(f"✅ Project summary saved: {summary_file}")
    
    # Final instructions
    print("\n" + "="*60)
    print("🎉 WORKFLOW SETUP COMPLETE!")
    print("="*60)
    print(f"📁 Project location: {project_folder}")
    print(f"📋 Summary document: {summary_file}")
    print("\n📌 IMMEDIATE NEXT STEPS:")
    print("1. Open ArcGIS Pro")
    print("2. Create a new project in the project folder")
    print("3. Add these layers:")
    print(f"   - Imagery Source: {source_name}")
    print(f"     Path/URL: {imagery_source}")
    print(f"   - Section boundaries: {os.path.basename(sections_shp)}")
    print("4. Review the section boundaries")
    print("5. Assign sections to team members")
    print("\n📞 Need help? Check the documentation folder for guides.")
    print("="*60)

if __name__ == "__main__":
    try:
        main_workflow()
    except KeyboardInterrupt:
        print("\n\n⏹️  Workflow cancelled by user")
    except Exception as e:
        print(f"\n❌ Error in workflow: {e}")
        print("Check that you're running this in ArcGIS Pro Python environment")
