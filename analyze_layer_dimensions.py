import arcpy
import math

# Get the active map and project
project = arcpy.mp.ArcGISProject("CURRENT")
map_ = project.activeMap
if not map_:
    map_ = project.listMaps()[0]

print(f"Working with map: '{map_.name}'")

# Directly get the Imagery_2024 layer
target_layer_name = "Imagery_2024"
all_layers = map_.listLayers()

# Find the specific layer by name
layer = None
for lyr in all_layers:
    if lyr.name == target_layer_name:
        layer = lyr
        break

if not layer:
    print(f"Error: Could not find layer '{target_layer_name}' in the map.")
    print("Available layers:")
    for lyr in all_layers:
        print(f"  - {lyr.name}")
    exit(1)

print(f"Found and using layer: '{layer.name}'")

# Get extent and properties of the layer
desc = arcpy.Describe(layer)
extent = desc.extent

# Calculate layer dimensions
layer_width = extent.XMax - extent.XMin
layer_height = extent.YMax - extent.YMin

print(f"\n=== LAYER ANALYSIS ===")
print(f"Layer Name: {layer.name}")
print(f"Extent: {extent.XMin:.2f}, {extent.YMin:.2f}, {extent.XMax:.2f}, {extent.YMax:.2f}")
print(f"Layer Width: {layer_width:.2f} meters")
print(f"Layer Height: {layer_height:.2f} meters")

# Get pixel information if available
try:
    cell_size_x = desc.meanCellWidth if hasattr(desc, 'meanCellWidth') else 1.0
    cell_size_y = desc.meanCellHeight if hasattr(desc, 'meanCellHeight') else 1.0
    print(f"Cell Size: {cell_size_x} x {cell_size_y} meters")
    
    # Calculate pixels
    pixels_width = layer_width / cell_size_x
    pixels_height = layer_height / cell_size_y
    print(f"Layer Size in Pixels: {pixels_width:.0f} x {pixels_height:.0f}")
except Exception as e:
    print(f"Could not determine cell size: {e}")
    cell_size_x = cell_size_y = 1.0

print(f"\n=== TILE SIZE RECOMMENDATIONS ===")

# Test different grid sizes and calculate optimal tile sizes
grid_sizes = [2, 3, 4, 5, 6, 8, 10, 12, 16, 20]

print("Grid Size | Tile Width | Tile Height | Width Pixels | Height Pixels | Notes")
print("----------|------------|-------------|--------------|---------------|------")

for grid_size in grid_sizes:
    tile_width = layer_width / grid_size
    tile_height = layer_height / grid_size
    
    # Calculate pixels per tile
    tile_pixels_width = tile_width / cell_size_x
    tile_pixels_height = tile_height / cell_size_y
    max_tile_pixels = max(tile_pixels_width, tile_pixels_height)
    
    # Check if tiles are reasonably square
    aspect_ratio = tile_width / tile_height
    is_square = 0.8 <= aspect_ratio <= 1.2
    
    # Check if tile size is reasonable for server limits
    pixel_note = ""
    if max_tile_pixels > 2000:
        pixel_note = "⚠️ Large"
    elif max_tile_pixels > 1000:
        pixel_note = "🔶 Medium"
    else:
        pixel_note = "✅ Safe"
    
    square_note = "📐 Square" if is_square else "⚪ Rect"
    
    print(f"{grid_size:^9} | {tile_width:^10.0f} | {tile_height:^11.0f} | {tile_pixels_width:^12.0f} | {tile_pixels_height:^13.0f} | {pixel_note} {square_note}")

print(f"\n=== RECOMMENDED CONFIGURATIONS ===")

# Find best options
best_options = []
for grid_size in grid_sizes:
    tile_width = layer_width / grid_size
    tile_height = layer_height / grid_size
    
    tile_pixels_width = tile_width / cell_size_x
    tile_pixels_height = tile_height / cell_size_y
    max_tile_pixels = max(tile_pixels_width, tile_pixels_height)
    
    aspect_ratio = tile_width / tile_height
    is_reasonably_square = 0.8 <= aspect_ratio <= 1.2
    is_safe_size = max_tile_pixels <= 1000
    
    if is_reasonably_square and is_safe_size:
        total_tiles = grid_size * grid_size
        best_options.append({
            'grid_size': grid_size,
            'tile_width': tile_width,
            'tile_height': tile_height,
            'total_tiles': total_tiles,
            'max_pixels': max_tile_pixels
        })

if best_options:
    print("Recommended grid configurations (safe pixel count + reasonably square tiles):")
    for option in best_options[:5]:  # Show top 5
        print(f"  • {option['grid_size']}x{option['grid_size']} grid = {option['total_tiles']} tiles")
        print(f"    Tile size: {option['tile_width']:.0f}m x {option['tile_height']:.0f}m")
        print(f"    Max pixels per tile: {option['max_pixels']:.0f}")
        print()
else:
    print("⚠️ No ideal configurations found with current constraints.")
    print("Consider using a larger grid size or accepting larger tile pixel counts.")

print(f"\n=== CUSTOM TILE SIZE CALCULATOR ===")
print("To calculate grid size for a specific tile size:")
print(f"  For tile size X meters: Grid size = {layer_width:.0f} / X (width) and {layer_height:.0f} / X (height)")
print(f"  Example: For 500m tiles: Width grid = {layer_width/500:.1f}, Height grid = {layer_height/500:.1f}")
print(f"  Example: For 1000m tiles: Width grid = {layer_width/1000:.1f}, Height grid = {layer_height/1000:.1f}")
print(f"  Example: For 2000m tiles: Width grid = {layer_width/2000:.1f}, Height grid = {layer_height/2000:.1f}")

print(f"\n=== NOTES ===")
print("• 'Safe' pixel count: ≤1000 pixels per tile (conservative for web services)")
print("• 'Medium' pixel count: 1000-2000 pixels per tile (may work but risky)")
print("• 'Large' pixel count: >2000 pixels per tile (likely to cause server errors)")
print("• Square tiles are generally preferred for most analyses")
print("• All tiles in a grid will be exactly the same size (no edge tile issues)")
