# WATERLOO 2025 IMAGERY CLASSIFICATION GUIDE

## 📊 Input Options Comparison

| Aspect | 2025 Web Service | 2025 Local Mosaic |
|--------|------------------|-------------------|
| **Data Source** | 2025 imagery via web service | 2025 imagery as local file |
| **Access Method** | Service URL | Local file/geodatabase |
| **Processing Speed** | Limited by web service | Full local processing speed |
| **Storage Required** | Minimal (stream from web) | Full dataset (~1TB) |
| **Offline Capability** | No | Yes |
| **Team Distribution** | Easy sharing via URL | Need to distribute data files |

## 🚀 Simplified Workflow

### **Option 1: 2025 Web Service**
**Best for:** Quick access, easy team sharing, limited storage

```python
# Run the main workflow
exec(open('waterloo_classification_workflow.py').read())
# Select Option 1: 2025 Web Service
```

**Advantages:**
- ✅ No data download required
- ✅ Easy to share with team
- ✅ Minimal storage requirements
- ✅ Latest 2025 data
- ✅ Automatic boundary masking to exclude blank areas
- ✅ Auto-generated training polygons ready for labeling

**Limitations:**
- ⚠️ Dependent on internet connection
- ⚠️ Web service rate limits

### **Option 2: 2025 Local Mosaic**
**Best for:** Production work, offline capability, maximum speed

```python
# Run the main workflow
exec(open('waterloo_classification_workflow.py').read())
# Select Option 2: Local 2025 Mosaic
```

**Advantages:**
- ✅ Latest 2025 data
- ✅ Full processing speed
- ✅ Offline capability
- ✅ Complete control over processing
- ✅ No web service limitations
- ✅ Automatic boundary masking to exclude blank areas
- ✅ Auto-generated training polygons ready for labeling

**Requirements:**
- 💾 ~1TB storage space
- 🖥️ Sufficient RAM for processing
- 📁 Local mosaic file/geodatabase

## 📋 Step-by-Step Implementation

### **Core Workflow (Same for Both Options):**

#### **Step 1: Choose Your Data Source**
```python
# Run main workflow
python waterloo_classification_workflow.py
```
- **Option 1:** Provide 2025 web service URL
- **Option 2:** Provide path to local 2025 mosaic file

#### **Step 2: Create Boundary Mask**
The workflow will automatically create boundary masks to:
- **Exclude NoData/blank regions** from processing
- **Define actual imagery coverage** area
- **Optimize processing** by focusing only on data-rich areas
- **Improve team efficiency** by avoiding blank tile processing

#### **Step 3: Create Geographic Sections**
- Automatically divides imagery into manageable sections
- Sections sized for team distribution (4-8 sections recommended)
- Each section becomes independent work unit

#### **Step 3: Generate Training Polygons**
- **Automatically creates** training polygons for each section
- **Hexagonal sampling pattern** with user-selected size (5m, 10m, or 15m)
- **Grid-based + random sampling** for optimal coverage
- **150-300 polygons per section** based on area size

#### **Step 4: Team Distribution**
- Each team member gets assigned section(s)
- **Pre-generated training polygons** ready for labeling
- Perform supervised classification
- Return classified results

#### **Step 5: Combine Results**
```python
# Combine all section classifications
python combine_classifications.py
```

## 🔧 Technical Setup

### **For Web Service Users:**
- Ensure stable internet connection
- Test service accessibility before large processing jobs
- Consider processing during off-peak hours

### **For Local Mosaic Users:**
- Verify mosaic integrity and projection
- Ensure adequate disk space for processing
- Build pyramids/overviews for better performance

## 🔧 Technical Optimizations

### **For Both Input Types:**
```python
# Optimal processing settings:
# - Process sections individually
# - Clear intermediate datasets regularly
# - Monitor RAM usage during processing
# - Use appropriate coordinate system
```

### **File Organization:**
```
Project_Folder/
├── data/
│   ├── 2025_mosaic_data/     # If using local files
│   └── boundaries/           # Optional boundary masks
├── sections/
│   ├── section_01/
│   ├── section_02/
│   └── ...
├── training_data/
├── classified_results/
└── final_outputs/
```

## 🎯 Recommendations by Team Size

### **Small Team (2-3 people):**
- **Use web service** for easy access
- 4-6 sections
- Boundary masking automatically applied

### **Medium Team (4-6 people):**
- **Choose based on data availability** (web service or local)
- 6-8 sections
- Boundary masking optimizes team efficiency

### **Large Team (7+ people):**
- **Prefer local mosaic** for better performance
- 8-10 sections
- Boundary masking essential for large-scale processing

## 🚨 Important Considerations

### **Data Consistency:**
- Both options use same 2025 imagery data
- Workflow remains identical regardless of input method
- Results should be equivalent between web service and local file

### **Boundary Masking (Required):**
- **Always applied** to exclude blank/NoData areas
- **Automatically detects** actual imagery boundaries
- **Essential for** irregular imagery shapes and large datasets
- **Improves efficiency** by processing only data-rich regions

### **Performance Expectations:**

| Input Method | Processing Time per Section | Best Use Case |
|--------------|----------------------------|---------------|
| 2025 Web Service | 2-4 hours | Easy access, team sharing |
| 2025 Local Mosaic | 1-2 hours | Production work, speed |

## 📞 Quick Decision Guide

**Choose 2025 Web Service if:**
- Easy team access is priority
- Limited local storage space
- Good internet connectivity available
- Want to avoid data management

**Choose 2025 Local Mosaic if:**
- Maximum processing speed needed
- Offline capability required
- Have adequate storage space (1TB+)
- Prefer local data control

## 🛠️ Troubleshooting

### **Common Issues with Web Services:**
1. **Slow response** → Check internet connection, try off-peak hours
2. **Service timeouts** → Reduce section sizes
3. **Authentication errors** → Verify service URL and accessibility
4. **Rate limiting** → Add processing delays

### **Common Issues with Local Files:**
1. **Large file sizes** → Use section-based processing
2. **Memory errors** → Reduce processing area or increase RAM
3. **Slow performance** → Check disk I/O, use SSD storage
4. **File corruption** → Verify data integrity, rebuild if needed

## 📈 Next Steps

1. **Identify your 2025 data source** (web service URL or local file path)
2. **Choose appropriate input method** based on your constraints
3. **Run the main workflow** (waterloo_classification_workflow.py)
4. **Boundary masking and training polygons will be automatically created**
5. **Distribute sections to team members with pre-generated training polygons**
6. **Team members label polygons and perform supervised classification**
6. **Quality control and combine results**

---

*This guide focuses on 2025 Waterloo imagery with flexible input options. The same workflow handles both web service and local file inputs seamlessly.*
