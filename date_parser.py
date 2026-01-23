import re
from datetime import date, time, timedelta
from typing import Dict, Optional, List

month_names = ["january", "february", "march", "april", "may", "june",
               "july", "august", "september", "october", "november", "december"]

# return value = list of strings in iso format, e.g. ['YYYY-MM-DD', '2026-04-05']

# def keyword_check(message: str) -> List[date]:
#     pattern = r'month of (\w+)\s+(\d{4})\s*'
#     match = re.findall(pattern, message, flags=re.IGNORECASE)
#     if match:
#         year = int(match[0][1])
#         for i, month in enumerate(month_names, 1):
#             m_idx = re.findall(rf'\b({month}|{month[:3]})\s*', message)
#             if m_idx:
#                 month = i
#                 break
#         start_obj = date(year, month, 1)
#         end_obj = date(year, month, 31)
#     return None

def validate(date_list: List) -> List:
    obj_list = []
    # converts each entry to a datetime string in iso format
    for d in date_list:
        date_object = date(int(d[2]), int(d[0]), int(d[1])).isoformat()
        obj_list.append(date_object)
    
    # ensures the start date of the range is listed first
    obj_list.sort()
    return obj_list

def extractDate(message: str) -> List[date]:  
    # check for date in iso format
    iso_check = r'(\d{4}-\d{2}-\d{2})'
    iso_match = re.findall(iso_check, message)
    if iso_match:
        iso_match.sort()
        return iso_match

    date_list = []
    # check for year/s in user input
    year_check = rf'\s[0-9][0-9][0-9][0-9]'
    year_match = re.findall(year_check, message, flags=re.IGNORECASE)
    if len(year_match) > 1:
        # if there is more than one year, pass a new pattern to match each year with each date
        year_regex = rf'\w*,?\s*(\d{{4}})'
    else:
        # if only one year or none, pass empty pattern
        year_regex = '()'

    # check for date ranges in the same month, e.g. '3-20', or '4th to 21st'
    range_check = rf'\s(\d{{1,2}})(st|nd|rd|th)?\s*(to|-)\s*(\d{{1,2}})(st|nd|rd|th)?'
    range_match = re.findall(range_check, message, flags=re.IGNORECASE)
    if range_match:
        # if date range is found, pass a new pattern to bypass the date check
        date_regex = rf'\w*\s*(to|-)?\s*\w*'
    else:
        # if no date range in the same month, check for the date beside the month
        date_regex = rf'(\d{{1,2}})'

    # check for month, and associated year if any
    for i, month in enumerate(month_names, 1):
        # case where date is given before month, e.g. 6 April
        month_check = date_regex + rf'\w*\s+({month}|{month[:3]})\s*' + year_regex
        month_match = re.findall(month_check, message, flags=re.IGNORECASE)
        date_idx = 0

        if not month_match:
            # case where month is given before date, e.g. April 6
            month_check = rf'\b({month}|{month[:3]})\s*' + date_regex + year_regex
            month_match = re.findall(month_check, message, flags=re.IGNORECASE)
            date_idx = 1

        if month_match:
            for m in month_match:
                if m[2]:
                    year = m[2]
                elif year_match:
                    year = year_match[0]
                else:
                    year = str(date.today().year)
                obj = [str(i), m[date_idx], year]
                date_list.append(obj)
    
    # assemble the date range
    if range_match:
        # add another entry
        date_list.append(date_list[0])
        # replace the empty dates to the results extracted by range_match
        date_list[0] = [date_list[0][0], range_match[0][0], date_list[0][2]]
        date_list[1] = [date_list[0][0], range_match[0][3], date_list[0][2]]
    
    iso_list = validate(date_list)
    # print(iso_list)
    return iso_list