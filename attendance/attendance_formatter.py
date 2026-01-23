# attendance/attendance_formatter.py - Response Formatting
from typing import Dict

def format_presence_check(result: Dict) -> str:
    """Format presence check response"""
    if not result['present']:
        return f"❌ **{result['employee_identifier']}** is **NOT PRESENT** on {result['date']}.\n\n💡 They have no attendance records for this date."
    
    if result['matches'] == 1:
        # Single employee found
        emp_name = list(result['employees'].keys())[0]
        records = result['employees'][emp_name]
        
        output = f"✅ **Yes, {result['employee_identifier']}** is **PRESENT** on {result['date']}!\n\n"
        output += f"**Employee:** {emp_name}\n"
        output += f"**Records:** {len(records)}\n\n"
        output += "**Timeline:**\n"
        
        for idx, record in enumerate(records, 1):
            timestamp = record['timestamp'].strftime('%I:%M %p')
            rec_type = record.get('type', 'Entry')
            location = record.get('location', 'Unknown')
            output += f"{idx}. {timestamp} - {rec_type} 📍 **{location}**\n"
        
        return output
    
    else:
        # Multiple employees matched
        output = f"🔍 Found **{result['matches']} employees** matching '{result['employee_identifier']}':\n\n"
        
        for idx, (emp_name, records) in enumerate(result['employees'].items(), 1):
            output += f"### {idx}. {emp_name}\n"
            output += f"   - Records: {len(records)}\n"
            first_entry = records[0]['timestamp'].strftime('%I:%M %p')
            location = records[0].get('location', 'Unknown')
            output += f"   - First entry: {first_entry} 📍 {location}\n\n"
        
        output += "💡 **Tip:** Use full name or employee number for specific results."
        return output

def format_date_query(result: Dict) -> str:
    """Format date-specific query response"""
    total_records = result.get('total_records', 0)
    
    if total_records == 0:
        msg = f"❌ **{result.get('employee_identifier', 'No one')}** was **NOT PRESENT** on **{result['date']}**"
        if result.get('employee_identifier'):
            msg += "\n\n💡 They have no attendance records for this date."
        return msg
    
    # Check if this is a single employee query
    if result.get('employee_identifier') and result['unique_employees'] <= 3:
        if result['unique_employees'] == 1:
            emp_name = list(result['employees'].keys())[0]
            records = result['employees'][emp_name]
            
            output = f"✅ **Yes, {result['employee_identifier']}** was **PRESENT** on **{result['date']}**!\n\n"
            output += f"**Employee:** {emp_name}\n"
            output += f"**Records:** {len(records)}\n\n"
            output += "**Timeline:**\n"
            
            for idx, record in enumerate(records, 1):
                timestamp = record['timestamp'].strftime('%I:%M %p')
                rec_type = record.get('type', 'Entry')
                location = record.get('location', 'Unknown')
                output += f"{idx}. {timestamp} - {rec_type} 📍 **{location}**\n"
            
            return output
        else:
            output = f"🔍 Found **{result['unique_employees']} employees** matching '{result['employee_identifier']}' on **{result['date']}**:\n\n"
            
            for idx, (emp_name, records) in enumerate(result['employees'].items(), 1):
                output += f"### {idx}. {emp_name}\n"
                output += f"   - Records: {len(records)}\n"
                first_entry = records[0]['timestamp'].strftime('%I:%M %p')
                location = records[0].get('location', 'Unknown')
                output += f"   - First entry: {first_entry} 📍 {location}\n\n"
            
            output += "💡 **Tip:** Use full name or employee number for specific results."
            return output
    
    # General date query
    output = f"# 📅 Attendance for {result['date']}\n\n"
    
    if result.get('employee_identifier'):
        output += f"**Employee Filter:** {result['employee_identifier']}\n"
    
    output += f"**Unique Employees:** {result['unique_employees']}\n"
    output += f"**Total Records:** {result['total_records']}\n\n"
    
    output += "## 👥 Employee Records:\n\n"
    for emp_name, records in list(result['employees'].items())[:20]:
        output += f"### {emp_name}\n"
        output += f"**Entries:** {len(records)}\n"
        for record in records[:5]:
            timestamp = record['timestamp'].strftime('%I:%M %p')
            rec_type = record.get('type', 'Entry')
            location = record.get('location', 'Unknown')
            output += f"   - {timestamp}: {rec_type} 📍 {location}\n"
        output += "\n"
    
    if result['unique_employees'] > 20:
        output += f"*Showing first 20 of {result['unique_employees']} employees*\n"
    
    return output

def format_range_query(result: Dict) -> str:
    """Format date range query response"""
    total_records = result.get('total_records', 0)
    
    if total_records == 0:
        msg = f"❌ "
        if result.get('employee_identifier'):
            msg += f"**{result['employee_identifier']}** has no records from {result['start_date']} to {result['end_date']}"
        else:
            msg += f"No records found from {result['start_date']} to {result['end_date']}"
        return msg
    
    output = f"# 📊 Attendance Report\n\n"
    output += f"**Period:** {result['start_date']} to {result['end_date']}\n"
    
    if result.get('employee_identifier'):
        output += f"**Employee:** {result['employee_identifier']}\n"
    
    output += f"**Unique Employees:** {result['unique_employees']}\n"
    output += f"**Total Records:** {result['total_records']}\n\n"
    
    output += "## 📅 Daily Breakdown:\n\n"
    
    for emp_name, dates in list(result['employees'].items())[:10]:
        output += f"### {emp_name}\n"
        output += f"**Days present:** {len(dates)}\n\n"
        
        for record_date, records in sorted(dates.items())[:7]:
            output += f"**{record_date}:** {len(records)} entries\n"
            for record in records[:3]:
                timestamp = record['timestamp'].strftime('%I:%M %p')
                rec_type = record.get('type', 'Entry')
                location = record.get('location', 'Unknown')
                output += f"   - {timestamp}: {rec_type} 📍 {location}\n"
        output += "\n"
    
    if result['unique_employees'] > 10:
        output += f"*Showing first 10 of {result['unique_employees']} employees*\n"
    
    return output

def format_count_operators(result: Dict) -> str:
    """Format operator count response"""
    if 'error' in result:
        return f"❌ **Error:** {result['error']}"
    
    output = f"# 👥 Operators Present\n\n"
    output += f"**Date:** {result['date']}\n"
    output += f"**Time threshold:** After {result['start_time']}\n"
    output += f"**Total operators:** {result['count']}\n\n"
    
    if result['count'] > 0:
        output += "## Operators List:\n\n"
        for idx, op in enumerate(result['operators'], 1):
            first_entry = op['first_entry'].strftime('%I:%M %p')
            location = op.get('location', 'Unknown')
            output += f"{idx}. **{op['employee_name']}** ({op['employee_num']}) - {first_entry} 📍 **{location}**\n"
    else:
        output += "❌ No operators clocked in after the specified time.\n"
    
    return output

def format_absent_employees(result: Dict) -> str:
    """Format absent employees response"""
    if 'error' in result:
        return f"❌ **Error:** {result['error']}"
    
    output = f"# 🚫 Absent Employees\n\n"
    output += f"**Date:** {result['date']}\n"
    output += f"**Total Employees:** {result['total_employees']}\n"
    output += f"**Present:** {result['present']}\n"
    output += f"**Absent:** {result['absent']}\n\n"
    
    if result['absent'] > 0:
        output += "## Absent List:\n\n"
        for idx, emp in enumerate(result['absent_list'], 1):
            output += f"{idx}. **{emp['name']}** ({emp['num']})\n"
    else:
        output += "✅ All employees are present!\n"
    
    return output

def format_latest_entries(result: Dict) -> str:
    """Format latest entries response"""
    if 'error' in result:
        return f"❌ **Error:** {result['error']}"
    
    output = f"# 🕐 Latest Attendance Entries\n\n"
    output += f"**Count:** {result['count']}\n\n"
    
    for idx, record in enumerate(result['latest_entries'], 1):
        timestamp = record['timestamp'].strftime('%Y-%m-%d %I:%M %p')
        location = record.get('location', 'Unknown')
        output += f"{idx}. **{record['employee_name']}** ({record['employee_num']})\n"
        output += f"   - Time: {timestamp}\n"
        output += f"   - Type: {record.get('type', 'N/A')}\n"
        output += f"   - Location: 📍 {location}\n\n"
    
    return output

def format_response(result: Dict, query_type: str) -> str:
    """Main formatter - routes to appropriate format function"""
    if 'error' in result:
        return f"❌ **Error:** {result['error']}"
    
    formatters = {
        'presence_check': format_presence_check,
        'date_query': format_date_query,
        'range_query': format_range_query,
        'count_operators': format_count_operators,
        'absent': format_absent_employees,
        'latest': format_latest_entries
    }
    
    formatter = formatters.get(query_type)
    if formatter:
        return formatter(result)
    
    return "❓ Unknown query type"