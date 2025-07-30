# ArcGIS Tile Processing & Mosaic Creation Suite

A comprehensive collection of Python scripts for processing large-scale imagery datasets in ArcGIS Pro, designed for tiling huge service layers and creating mosaic datasets for supervised classification and analysis.

## 🎯 Overview

This repository contains scripts for:
- **Tile Generation**: Split large imagery layers into manageable tiles
- **Test Processing**: Validate workflows with small datasets
- **Mosaic Creation**: Combine tiles back into seamless datasets
- **Training Data Generation**: Create random sampling polygons for supervised classification
- **Data Management**: Clean and optimize tiles for processing

## 📋 Prerequisites

- **ArcGIS Pro** (recommended version 3.0+)
- **ArcPy** (included with ArcGIS Pro)
- **Spatial Analyst Extension** (for raster processing)
- **Image Analyst Extension** (recommended for advanced operations)

## 🗂️ Script Categories & Usage

### 🔷 **PRODUCTION SCRIPTS** (Full-Scale Processing)

#### 1. `script_full_extent_tiles.py` ⭐ **[MAIN PRODUCTION SCRIPT]**
**Purpose**: Process entire imagery layers into ~150,000 tiles for large-scale analysis

**Key Features**:
- Batch processing with retry logic
- Comprehensive logging and error tracking
- Time estimation and progress monitoring
- Server-friendly processing with delays

**⚠️ REQUIRED CHANGES**:
```python
output_dir = r"C:\change\to\your\directory" #change to match your output directory
```

**Configuration Options**:
- `tile_size = 250` (meters)
- `batch_size = 50` (tiles per batch)
- `max_retries = 3`
- `sleep_between_batches = 10` (seconds)

**Usage**:
1. Open ArcGIS Pro with your imagery layer loaded
2. Ensure layer is named "Imagery_2024"
3. Update `output_dir` path
4. Run in Python window or notebook
5. Monitor logs for progress

**Estimated Time**: 40-60 hours for 150K tiles
**Storage**: ~500GB output

---

#### 2. `script_large_data_strategy.py`
**Purpose**: Handle 1TB+ datasets with advanced error recovery

**Key Features**:
- 500m tiles for faster processing
- Enhanced retry mechanisms
- Failed tile tracking
- Processing time estimation

**⚠️ REQUIRED CHANGES**:
```python
output_dir = r"directory/path/to/output"  # Update this path
```

**Usage**: Same as main script, but for extremely large datasets

---

### 🔷 **TEST SCRIPTS** (Validation & Small-Scale Testing)

#### 3. `test_batch_tiles.py` ⭐ **[RECOMMENDED FOR TESTING]**
**Purpose**: Test processing workflow with limited tiles before full production

**Key Features**:
- Processes only 100 tiles for validation
- Performance benchmarking
- Full dataset projections
- Success rate analysis

**⚠️ REQUIRED CHANGES**:
```python
output_dir = r"directory/path/to/output"  # Change to your output directory
max_test_tiles = 100  # Change number of test tiles (recommended: 50-200)
batch_size = 25       # Adjust for your system
```

**Usage**:
1. **ALWAYS RUN THIS FIRST** before production processing
2. Update output directory path
3. Adjust `max_test_tiles` (50-200 recommended)
4. Review success rate and performance metrics
5. Use results to optimize production settings

---

#### 4. `test_optimized_tiles.py`
**Purpose**: Performance testing with different tile sizes

**⚠️ REQUIRED CHANGES**:
```python
# Update paths and test parameters as needed
```

---

#### 5. `optimized_script_full_extent_100tiles_trial.py`
**Purpose**: 100-tile validation script with optimized processing

**⚠️ REQUIRED CHANGES**:
```python
# Update output directory and tile count
```

---

### 🔷 **MOSAIC CREATION SCRIPTS**

#### 6. `test_mosaic_creation.py`
**Purpose**: Test mosaic dataset creation with existing tiles

**Key Features**:
- Creates geodatabase mosaic datasets
- Validates tile compatibility
- Tests seamless mosaicking

**⚠️ REQUIRED CHANGES**:
```python
tiles_folder = r"C:\Users\dheaven\Desktop\testing_tiles"  # Your tiles folder
output_gdb = r"C:\Users\dheaven\Desktop\test_mosaic.gdb"  # Output location
```

**Usage**:
1. Ensure you have test tiles created
2. Update folder paths
3. Run to validate mosaic creation workflow

---

#### 7. `clean_tiles_for_mosaic.py`
**Purpose**: Pre-process tiles before mosaic creation

**Key Features**:
- Removes tiles with excessive NoData
- Optimizes tiles for seamless mosaicking
- Quality control analysis

**⚠️ REQUIRED CHANGES**:
```python
# Update folder paths in the function calls at bottom of script
```

---

### 🔷 **TRAINING DATA GENERATION SCRIPTS**

#### 8. `set_random_points.py` ⭐ **[UPDATED - ARCPY COMPATIBLE]**
**Purpose**: Generate random sampling polygons for supervised classification

**Key Features**:
- Creates square, circular, or hexagonal polygons
- NoData validation
- Multiple polygon shapes
- **Pure ArcPy implementation** (no external libraries)

**⚠️ REQUIRED CHANGES**:
```python
tiles_dir = r"/Users/doraliu/Desktop/tiles_250m_full"  # Update to your tiles folder
num_polygons = 50  # Change number of polygons per tile (recommended: 25-100)
polygon_size = 2   # Size in meters (adjust based on your needs)
polygon_shape = 'hexagon'  # Options: 'square', 'circle', 'hexagon'
```

**Usage**:
1. Update `tiles_dir` to your tiles folder
2. Adjust `num_polygons` (25-100 per tile recommended)
3. Choose polygon shape and size
4. Run directly in ArcGIS Pro Python window

---

#### 9. `set_random_polygons.py`
**Purpose**: Alternative polygon generation script

**⚠️ REQUIRED CHANGES**:
```python
# Update paths and polygon parameters
```

---

### 🔷 **LEGACY/ALTERNATIVE SCRIPTS**

#### 10. `segment_into_tiles.py`
**Purpose**: Alternative tiling approach using ArcGIS API for Python
**Note**: Requires external `arcgis` package installation

#### 11. `segment_into_tiles_url.py`
**Purpose**: URL-based tiling approach
**Note**: May require additional authentication setup

---

## 🚀 Quick Start Guide

### Step 1: Test Your Workflow
```python
# 1. Run test_batch_tiles.py first
# 2. Update output_dir path
# 3. Set max_test_tiles = 100
# 4. Review success rate and performance
```

### Step 2: Generate Training Polygons
```python
# 1. Run set_random_points.py on test tiles
# 2. Update tiles_dir path
# 3. Set num_polygons = 50
# 4. Choose polygon_shape = 'hexagon'
```

### Step 3: Test Mosaic Creation
```python
# 1. Run test_mosaic_creation.py
# 2. Update tiles_folder and output_gdb paths
# 3. Validate mosaic workflow
```

### Step 4: Full Production Processing
```python
# 1. Run script_full_extent_tiles.py
# 2. Update output_dir path
# 3. Monitor logs and progress
# 4. Estimated time: 40-60 hours
```

## ⚙️ Configuration Guidelines

### Tile Size Recommendations:
- **250m tiles**: Good balance of processing speed and detail
- **500m tiles**: Faster processing for very large datasets
- **100m tiles**: Higher detail, slower processing

### Batch Size Guidelines:
- **Small datasets**: batch_size = 25-50
- **Large datasets**: batch_size = 50-100
- **System limitations**: Reduce if memory issues occur

### Test Parameters:
- **Initial testing**: max_test_tiles = 50-100
- **Performance validation**: max_test_tiles = 200-500
- **Polygon generation**: num_polygons = 25-100 per tile

## 📊 Expected Performance

### Processing Rates:
- **250m tiles**: ~30-50 tiles/minute
- **500m tiles**: ~60-80 tiles/minute
- **Full 150K tiles**: 40-60 hours total

### Storage Requirements:
- **250m tiles**: ~3-5 MB per tile
- **150K tiles**: ~500GB total storage
- **Mosaic datasets**: 10-20% of tile storage

## 🛠️ Troubleshooting

### Common Issues:

1. **ModuleNotFoundError**: Use ArcPy-compatible scripts (marked as such)
2. **Path Errors**: Always use absolute paths, forward slashes on macOS
3. **Layer Not Found**: Check layer name is exactly "Imagery_2024"
4. **Memory Issues**: Reduce batch_size and add more sleep time
5. **Failed Tiles**: Check failed_tiles.txt log for specific errors

### Performance Tips:

1. **Always test first** with test_batch_tiles.py
2. **Monitor system resources** during processing
3. **Use SSD storage** for better I/O performance
4. **Close unnecessary applications** during processing
5. **Run during off-peak hours** for server processing

## 📁 Output Structure

```
output_directory/
├── batch_YYYYMMDD_HHMMSS/
│   ├── tile_r0001_c0001.tif
│   ├── tile_r0001_c0002.tif
│   ├── ...
│   ├── processing_log.txt
│   └── failed_tiles.txt
└── mosaics/
    └── mosaic_dataset.gdb
```

## 🎯 Best Practices

1. **Test Workflow**: Always run test scripts before production
2. **Path Configuration**: Update all directory paths before running
3. **Progress Monitoring**: Watch logs and performance metrics
4. **Data Backup**: Ensure original data is backed up
5. **System Resources**: Monitor CPU, memory, and disk usage
6. **Error Handling**: Review failed tiles logs and retry if needed

## 📝 Notes

- **Coordinate System**: Scripts use EPSG:26917 (NAD83 UTM Zone 17N)
- **File Naming**: Tiles use format `tile_rXXXX_cXXXX.tif`
- **Logging**: All operations are logged with timestamps
- **Retry Logic**: Failed operations are automatically retried
- **Batch Processing**: Server-friendly processing with delays

---

**Repository**: Segment-huge-service-layer-into-tiles  
**Author**: DChenxiLiu  
**Last Updated**: July 2025  
**ArcGIS Pro Compatibility**: 3.0+
