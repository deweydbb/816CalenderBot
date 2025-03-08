# import os
# import gspread
# from gspread_formatting import get_effective_format
# from dateutil.parser import parse
# from datetime import date, timedelta

# from slack import send_volunteer_warning_message, send_special_note_message, send_message
# from config import * # yeah this is kinda awful but I don't feel like improving it with a real config file


# def is_date(string):
#     """Attempt to parse a string into a date object. Otherwise return None"""
#     try:
#         return parse(string).date()
#     except ValueError:
#         return None

# def convert_dates(all_cells):
#     """Convert date-like strings in a 2D list to date objects."""
#     for row in range(len(all_cells)):
#         for col in range(len(all_cells[row])):
#             converted_date = is_date(all_cells[row][col])
#             # check if successfully converted the cell to a date and update it
#             if converted_date:
#                 all_cells[row][col] = converted_date

# def get_date_location(date, all_cells):
#     """
#     Finds the row and column of the given date in the given cells using 0 based indexing
#     Throws an error if the date is not found

#     """
#     for row_idx, row in enumerate(all_cells):
#         for col_idx, value in enumerate(row):
#             if value == date:
#                 return row_idx, col_idx  # Return the first occurrence
#     raise ValueError(f"Date: {date} not found in the calender")

# def is_special_cell(worksheet, row, col):
#     """
#     Determines if a cell is a "special cell" that does not include volunteer info by checking
#     if the background color is not gray
#     """
#     # need to offset 0 based indexing to convert row/column index into excel label. Ex: C15
#     label = gspread.utils.rowcol_to_a1(row + 1, col + 1)
#     try:
#         background_color = get_effective_format(worksheet, label).backgroundColor
#         return not (background_color.red == background_color.green and background_color.green == background_color.blue)
#     except AttributeError:
#         # cell does not have background color, assume is not special
#         False

# def get_voluneers_for_date(date, all_cells, worksheet):
#     """
#     Returns a tuple of two elements. The first is the list of volunteers for the shift. The second
#     Is the list of special cells, like new volunteer that the shift may need to know about
#     """
#     # find the location of the given date in the worksheet
#     row, col = get_date_location(date, all_cells)

#     # increment the row by one to go one cell under the date
#     row = row + 1

#     all_volunteers = []
#     special_rows = []

#     # go down each row until the next date is reached or the end of the sheet is reached
#     while type(all_cells[row][col]) is str and row < len(all_cells):
#         cell = all_cells[row][col]

#         # check if the cell is special or contains volunteer signup info
#         if is_special_cell(worksheet, row, col):
#             special_rows.append(cell)
#         else:
#             # get volunteers names. The cell may contain multiple volunteers sigining up separated
#             # by commas so split by commas and then remove any leading/trailing whitespace before
#             # adding the volunteers to the volunteers list
#             all_volunteers.extend(item.strip() for item in cell.split(","))

#         # go down to the next cell
#         row = row + 1

#     # remove any possibly blank cells
#     all_volunteers = [volunteer for volunteer in all_volunteers if volunteer.strip() not in (None, '')]
#     special_rows = [special_row for special_row in special_rows if special_row.strip() not in (None, '')]

#     return all_volunteers, special_rows

# def get_has_keyholder(volunteers):
#     return any(keyholder_mark in volunteer.lower() for keyholder_mark in KEYHOLDER_MARKS for volunteer in volunteers)

# def send_slack_messages():
#     # initiate google sheets connection with api key
#     api_key = os.getenv('google_api_key')
#     gc = gspread.api_key(api_key)

#     # identify the sheet to work with
#     sh = gc.open_by_key(SHEET_ID)

#     # get the first sheet as it appears on google sheets and assume it is the current years calender
#     current_calender = sh.get_worksheet(0)

#     # get the entire sheets as a 2D array
#     all_cells = current_calender.get_all_values()

#     # # converts any strings that are dates into date objects
#     # # if a cell is not a date, leave as is
#     convert_dates(all_cells)

#     # volunteers, special_rows = get_voluneers_for_date(date.today() + timedelta(days=6), all_cells, current_calender)
#     # has_keyholder = get_has_keyholder(volunteers)

#     # print(volunteers, has_keyholder, special_rows)

#     today = date.today()

#     for days_out in SHIFT_VOLUNTEER_WARNING_DAYS:
#         date_to_check = today + timedelta(days=days_out)
#         day_of_week = DAYS_OF_WEEK[date_to_check.weekday()]

#         if day_of_week in SHIFT_DAYS:
#             volunteers, _ = get_voluneers_for_date(today + timedelta(days=days_out), all_cells, current_calender)
#             has_keyholder = get_has_keyholder(volunteers)

#             if len(volunteers) < VOLUNTEER_THRESHOLD or not has_keyholder:
#                 send_volunteer_warning_message(day_of_week, date_to_check, volunteers, has_keyholder)

#     for days_out in SHIFT_SPECIAL_NOTES_DAYS:
#         date_to_check = today + timedelta(days=days_out)
#         day_of_week = DAYS_OF_WEEK[date_to_check.weekday()]

#         if day_of_week in SHIFT_DAYS:
#             _, special_cells = get_voluneers_for_date(today + timedelta(days=days_out), all_cells, current_calender)

#             if special_cells:
#                 send_special_note_message(day_of_week, date_to_check, special_cells)        


