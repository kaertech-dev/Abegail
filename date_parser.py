import re
from dateparser.search import search_dates
from datetime import datetime, date, time, timedelta
import calendar
from typing import Dict, Optional, List

month_names = ["january", "february", "march", "april", "may", "june",
               "july", "august", "september", "october", "november", "december"]

# return value = list of strings in iso format, e.g. ['YYYY-MM-DD', '2026-04-05']

def keyword_check(message: str) -> List[str]:
    date_list = []
    today = date.today()

    week_match = re.search(r'(?:l|p)ast\s+(\d*)\s*weeks?', message, re.IGNORECASE)
    if week_match:
        day_of_week = today.weekday() + 1 #days from closest Sunday
        num_weeks = int(week_match.group(1)) if week_match.group(1) else 1
        end_date = today - timedelta(days=day_of_week)
        start_date = end_date - timedelta(days=(num_weeks*7)-1)

        date_list.append(start_date.isoformat())
        date_list.append(end_date.isoformat())
        return date_list

    if 'today' in message:
        date_list.append(today.isoformat())
    elif 'yesterday' in message:
        date_list.append((today - timedelta(days=1)).isoformat())
    elif match := re.search(r'(?:l|p)ast\s+(\d+)\s+days?', message, re.IGNORECASE):
        days = int(match.group(1))
        date_list.append((today - timedelta(days=days)).isoformat())
        date_list.append(today.isoformat())
    elif match := re.search(r'this week', message, re.IGNORECASE):
        day_of_week = today.weekday()
        start_date = today - timedelta(days=day_of_week)
        date_list.append(start_date)
        date_list.append(today.isoformat())
    elif match := re.search(r'this month', message, re.IGNORECASE):
        num_days = today.day - 1
        start_date = today - timedelta(days=num_days)
        date_list.append(start_date)
        date_list.append(today.isoformat())
    elif match := re.search(r'(?:last|previous) month', message, re.IGNORECASE):
        prev = today.month - 1
        _, last_day = calendar.monthrange(today.year, prev)
        start_date = date(year=today.year, month=prev, day=1).isoformat()
        end_date = date(year=today.year, month=prev, day=last_day).isoformat()
        date_list.append(start_date)
        date_list.append(end_date)

    return date_list

def validate(date_list: List) -> List:
    obj_list = []
    # converts each entry to a datetime string in iso format
    for d in date_list:
        date_object = date(int(d[2]), int(d[0]), int(d[1])).isoformat()
        obj_list.append(date_object)
    
    # ensures the start date of the range is listed first
    obj_list.sort()
    return obj_list

def extractDate_new(message: str):
    current_date = date.today()
    final_dates = []
    found_years = re.findall(r'(?<!\w)(\d{4})(?!\w)', message) or [current_date.year]
    # print('years', found_years)

    start_span = r'(?:from|starting|beginning|since)\s*(?:from)?'
    end_span = r'\s*(?:up)?\s+(?:to|until|and|-)\s+'
    first_split = re.split(start_span, message.lower(), flags=re.IGNORECASE)
    # print('first', first_split)

    second_split = re.split(end_span, first_split[-1], flags=re.IGNORECASE)
    # print('second', second_split)
    found_months = [m for m in month_names if m in message or m[:3] in message]
    for str_chunk in second_split:
        relative_span = r'(?:last|past|previous|this)\s+(\d)*\s*(day|week|month)'
        if rel_match := re.search(relative_span, str_chunk, re.IGNORECASE):
            # print(rel_match.group(1), rel_match.group(2))
            ctr = rel_match.group(1) or 1
            if rel_match.group(2) == 'day':
                parsed_date = current_date - timedelta(days=ctr)
            elif rel_match.group(2) == 'week':
                parsed_date = current_date - timedelta(weeks=ctr)
            elif rel_match.group(2) == 'month':
                _, last_day = calendar.monthrange(current_date.year, current_date.month-1)
                parsed_date = date(year=current_date.year, month=current_date.month-1, day=last_day)
            final_dates.append(parsed_date)
            continue
        
        found_months = [m for m in month_names if m+' ' in str_chunk or m[:3]+' ' in str_chunk]
        # print('found_months', found_months)
        for fm in found_months:
            pattern = f"({fm}|{fm[:3]})" + r'\s+(\d{1,2})(?!\d)\s*(?:to|until|-)?\s*(\d{1,2})?(?!\d)'
            found_days = re.findall(pattern, str_chunk, re.IGNORECASE)
            # print('found_days', found_days)
            if len(found_days) == 0:
                start = fm + ' ' + '01' + ' ' + str(found_years[0])
                final_dates.append(datetime.strptime(start, r'%B %d %Y'))
                idx = month_names.index(fm) + 1
                _, last_day = calendar.monthrange(int(found_years[0]), idx)
                end = f"{fm} {last_day} {found_years[0]}"
                final_dates.append(datetime.strptime(end, r'%B %d %Y'))
            else:
                date_str = fm + ' ' + found_days[0][1] + ' ' + str(found_years[0])
                final_dates.append(datetime.strptime(date_str, r'%B %d %Y'))

                if found_days[0][2] != '':
                    date_str = fm + ' ' + found_days[0][2] + ' ' + str(found_years[-1])
                    # print(date_str)
                    final_dates.append(datetime.strptime(date_str, r'%B %d %Y'))
    
    # print('Final', final_dates)
    if len(final_dates) == 0:
        return []
    return [m.isoformat() for m in final_dates]

def extractDate(message: str, default='today') -> List[str]:
    # check for time markers
    kw = keyword_check(message)
    # print('KW check:', kw)
    if len(kw) > 0:
        return kw
    
    span = find_span(message)
    # print('Span:', span)
    if span:
        return span
    
    # check for date in iso format
    iso_check = r'(\d{4}-\d{2}-\d{2})'
    iso_match = re.findall(iso_check, message)
    # print('ISO date:', iso_match)
    if iso_match:
        iso_match.sort()
        return iso_match

    today = date.today()

    date_list = []
    # check for year/s in user input
    year_check = r'(?<!\d)\d{4}(?!\d+)'
    year_match = re.findall(year_check, message, flags=re.IGNORECASE)
    if len(year_match) > 1:
        # if there is more than one year, pass a new pattern to match each year with each date
        year_regex = rf'\w*,?\s*(\d{{4}})'
    elif len(year_match) == 1:
        # if only one year or none, pass empty pattern
        # year_regex = '()'
        year_regex = r'(\d{4})'
    else:
        year_regex = '()'

    # check for date ranges in the same month, e.g. '3-20', or '4th to 21st'
    range_check = r'\s(\d{{1,2}})(st|nd|rd|th)?\s*(to|-)\s*(\d{{1,2}})(st|nd|rd|th)?'
    range_match = re.findall(range_check, message, flags=re.IGNORECASE)
    if range_match:
        # if date range is found, pass a new pattern to bypass the date check
        date_regex = r'\w*\s*(to|-)?\s*\w*'
    else:
        # if no date range in the same month, check for the date beside the month
        date_regex = r'(\d{1,2})?,?\s*'

    # check for month, and associated year if any
    for i, month in enumerate(month_names, 1):
        # case where date is given before month, e.g. 6 April
        # month_check = date_regex + rf'\w*\s+({month}|{month[:3]}).?\s*' + year_regex
        # month_match = re.findall(month_check, message, flags=re.IGNORECASE)
        # date_idx = 0

        # if not month_match:
            # case where month is given before date, e.g. April 6
        month_check = rf'\s+({month}|{month[:3]})(?!\w)\.?\s*' + date_regex + year_regex
        month_match = re.findall(month_check, message, flags=re.IGNORECASE)
        # print(month_match)
        date_idx = 1

        if month_match:
            for m in month_match:
                if m[2]:
                    year = m[2]
                elif year_match:
                    year = year_match[0]
                else:
                    year = str(today.year)
                obj = [str(i), m[date_idx], year]
                date_list.append(obj)

    # assemble the date range
    if range_match:
        # add another entry
        date_list.append(date_list[0])
        # replace the empty dates to the results extracted by range_match
        date_list[0] = [date_list[0][0], range_match[0][0], date_list[0][2]]
        date_list[1] = [date_list[0][0], range_match[0][3], date_list[0][2]]
    
    if len(date_list) == 1 and date_list[0][1] == '':
        date_list.append(date_list[0])
        _, last_day = calendar.monthrange(today.year, int(date_list[0][0]))
        date_list[0] = [date_list[0][0], '1', date_list[0][2]]
        date_list[1] = [date_list[0][0], last_day, date_list[0][2]]

    # print('bfor vald8:', date_list)

    if date_list:
        iso_list = validate(date_list)
        # print(iso_list)
        return iso_list
    else:
        # print('Default')
        return [today.isoformat()] if default == 'today' else []

def find_span(message: str):
    curr_date = datetime.now()
    final_dates = []
    
    start_span = r'(?:from|starting|beginning|since)\s*(?:from)*\s+(\w+)\s*(\d{1,2})?'
    end_span = r'(?:to|until|and|-)\s*(\w+|\d{1,2})\s*(\d{1,2})?'

    found_start = re.findall(start_span, message.lower()) # returns [(month, date)]
    found_end = re.findall(end_span, message.lower()) # returns [(date, )] or [(month, date)]
    years_list = re.findall(r'(?<!\w)(\d{4})(?!\w)', message)

    if found_start:
        year = curr_date.year if len(years_list) == 0 else years_list[0]
        for m in month_names:
            if found_start[0][0] == m or found_start[0][0] == m[:3]:
                new_str = f"{m} " + found_start[0][1] + f' {year}'
                date_obj = datetime.strptime(new_str, r'%B %d %Y')
                final_dates.append(date_obj)
                break
    
    if found_end:
        year = curr_date.year if len(years_list) == 0 else years_list[-1]
        for m in month_names:
            if found_end[0][0] == m or found_end[0][0] == m[:3]:
                new_str = f"{m} " + found_end[0][1] + f' {year}'
                date_obj = datetime.strptime(new_str, r'%B %d %Y')
                final_dates.append(date_obj)
                break
    elif found_start:
        final_dates.append(curr_date)
    
    # print(final_dates)
    return [m.date().isoformat() for m in final_dates]