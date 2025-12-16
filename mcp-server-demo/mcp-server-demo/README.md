# 📥 Export Feature Guide

## Overview
Abegail can now export your company data in multiple formats:
- **CSV** - For data analysis in Excel, Google Sheets, or databases
- **Word** - For formal reports and documentation
- **Excel** - For spreadsheets with formatting and styling
- **PowerPoint** - For presentations and meetings

## Installation

First, install the required dependencies:

```bash
pip install -r requirements.txt
```

This will install:
- `python-docx` - For Word document generation
- `openpyxl` - For Excel file generation
- `python-pptx` - For PowerPoint presentation generation

## How to Use

### 1. **Ask a Question**
Type any question about your company data:
- "What is the total output for all operators today?"
- "Show me the productivity of operator KE0197"
- "List all operators working this week"

### 2. **Click Export Button**
After getting your answer, click the green **📥 Export** button in the chat input area.

### 3. **Choose Format**
Select your preferred format:
- **📄 CSV** - Simple spreadsheet format
- **📝 Word** - Professional document
- **📊 Excel** - Formatted spreadsheet
- **📊 PowerPoint** - Presentation slides

### 4. **File Downloads Automatically**
The file will be generated and downloaded to your Downloads folder!

## What Gets Exported

### CSV Files Include:
- All company data records
- Headers with field names
- Your question and answer (at the bottom)
- Easy to import into databases

**Example:**
```csv
operator_id,output,cycle_time,date
KE0197,72,45.5,2024-11-25
LL0069,85,42.3,2024-11-25
...

Query: What is the productivity of operator KE0197?
Answer: Operator KE0197 produced 72 units today.
```

### Word Documents Include:
- **Title Page** with report title and date
- **Query Summary** with your question and AI's answer
- **Data Table** with all records
- Professional formatting with bold headers
- Automatically sized columns

**Features:**
- ✅ Centered title
- ✅ Formatted tables
- ✅ Bold headers
- ✅ Clean layout

### Excel Files Include:
- **Title Section** with report name
- **Generated Date** timestamp
- **Query Summary** (if you asked a question)
- **Data Table** with:
  - Blue header row with white text
  - Auto-adjusted column widths
  - Professional formatting
- Multiple worksheets (if data is large)

**Features:**
- ✅ Colored headers
- ✅ Auto-sized columns
- ✅ Cell formatting
- ✅ Formulas support

### PowerPoint Presentations Include:
- **Slide 1:** Title slide with report name and date
- **Slide 2:** Query summary (your question & answer)
- **Slide 3+:** Data tables (8 rows per slide)
- Professional slide design
- Company branding ready

**Features:**
- ✅ Multiple slides for large datasets
- ✅ Formatted tables
- ✅ Page numbers
- ✅ Professional layout

## Use Cases

### 📊 **Excel - Best For:**
- Financial analysis
- Creating charts and graphs
- Running calculations
- Sharing with accounting team
- Pivot tables

### 📝 **Word - Best For:**
- Formal reports
- Documentation
- Company records
- Client reports
- Printing

### 📊 **PowerPoint - Best For:**
- Team meetings
- Executive presentations
- Client presentations
- Quarterly reviews
- Training materials

### 📄 **CSV - Best For:**
- Data import/export
- Database uploads
- Python/R analysis
- Simple data transfer
- Backup purposes

## Tips & Tricks

### 1. **Ask Before Exporting**
Always ask a question first to get context in your export:
```
✅ Good: "Show operator productivity" → Export
❌ Okay: Just click Export (gets all data but no context)
```

### 2. **Combine Multiple Exports**
- Export Excel for analysis
- Export PowerPoint for presentation
- Export CSV for backup

### 3. **Customize Exports**
Edit `app.py` to customize:
- Colors and styling
- Company logo
- Report format
- Additional fields

### 4. **Large Datasets**
For datasets with 100+ records:
- **PowerPoint**: Split into multiple slides (8 rows each)
- **Excel**: All data in one sheet with filters
- **Word**: May take longer to generate
- **CSV**: Fastest option

## Troubleshooting

### Export Button Not Working?
1. Check if data is available: `http://localhost:8080/api/test-data`
2. Check browser console for errors (F12)
3. Verify dependencies are installed: `pip list | grep -E "docx|openpyxl|pptx"`

### File Won't Download?
1. Check browser's download settings
2. Allow popups for localhost
3. Check Downloads folder permissions

### Export Takes Too Long?
- Large datasets take 5-15 seconds
- PowerPoint is slowest (multiple slides)
- CSV is fastest

### Missing Dependencies?
```bash
# Reinstall all dependencies
pip install -r requirements.txt --upgrade

# Or install individually
pip install python-docx openpyxl python-pptx
```

## Advanced Customization

### Add Company Logo to Word Documents

Edit `app.py` in the `export_word()` function:

```python
def export_word(data, question, answer):
    doc = Document()
    
    # Add logo
    doc.add_picture('company_logo.png', width=Inches(2))
    
    # ... rest of the code
```

### Custom Excel Styling

Edit `app.py` in the `export_excel()` function:

```python
# Change header color
header_fill = PatternFill(
    start_color="FF0000",  # Red
    end_color="FF0000",
    fill_type="solid"
)
```

### Add Charts to PowerPoint

```python
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

# Add chart slide
chart_data = CategoryChartData()
chart_data.categories = ['Q1', 'Q2', 'Q3', 'Q4']
chart_data.add_series('Sales', (50, 60, 70, 80))

slide = prs.slides.add_slide(prs.slide_layouts[6])
chart = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(2), Inches(2), Inches(6), Inches(4),
    chart_data
).chart
```

## API Endpoint

You can also export programmatically:

```javascript
// Export via JavaScript
fetch('/api/export/excel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        type: 'all',
        question: 'Show all operators',
        answer: 'Here are all operators...',
        session_id: 'session_123'
    })
})
.then(response => response.blob())
.then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'data.xlsx';
    a.click();
});
```

## Support

For issues or feature requests:
1. Check the console logs: `python app.py`
2. Test the endpoint: `http://localhost:8080/api/test-data`
3. Verify file permissions in the output directory

---

**Happy Exporting! 📥**