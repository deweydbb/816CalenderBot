import azure.functions as func
import logging

import os
import gspread
# from gspread_formatting import get_effective_format
from dateutil.parser import parse
from datetime import datetime, date, timedelta

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# do not change (for internal use of the program to map numbers to days)
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]



### START OF CONFIG ###

# Can find in the URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/
SHEET_ID="1_qWl72k-m8rl9aYLkcvEc1tzHtNEU-Dki0gAdRTIuj0"
# must be of the form https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit
SHEET_URL=f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

# text people can put after their name to indicate to the bot they are keyholder
KEYHOLDER_MARKS=['🔑', 'keyholder']

# Days where the shop is open
SHIFT_DAYS = ['Monday', 'Thursday', 'Saturday']
# day of the week mapped to the slack channel to send the message in
# channel format is #{name of channel}
SHIFT_DAY_TO_CHANNEL = {
    'Monday': '#bot-tester',
    'Thursday': '#bot-tester',
    'Saturday': '#bot-tester'
}
if set(SHIFT_DAY_TO_CHANNEL.keys()) != set(SHIFT_DAYS):
    raise KeyError("SHIFT_DAYS and SHIFT_DAY_TO_CHANNEL must have the same days") 



# How many days out should the low volunteer warning and no keyholder warning be sent 
SHIFT_VOLUNTEER_WARNING_DAYS = [6, 3, 0]
# How many days out should the special notes for shift be sent out. 
SHIFT_SPECIAL_NOTES_DAYS = [0]

# if under number of volunteers signed up for shift, send warning
VOLUNTEER_THRESHOLD = 3



#
#
# Start of Slack
#
#

slack_token = os.getenv('slack_token')
client = WebClient(token=slack_token)

def send_message(channel_id, message):
    """Send the given message to the specified channel"""
    try:
        # Sending a message to the specified Slack channel
        client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        logging.info(f"Message sent successfully")
    except SlackApiError as e:
        logging.error(f"Error sending message: {e.response['error']}")

def get_volunteer_list(volunteers):
    """Get a comma separated list of volunteers where the last volunteers are separated by ', and'"""
    if len(volunteers) < 2:
        return volunteers[0]

    # Join all but the last element with commas
    comma_separated = ", ".join(volunteers[:-1])

    # Add "and" before the last element
    return f"{comma_separated} and {volunteers[-1]}"

def get_keyholder_marks_list():
    if len(KEYHOLDER_MARKS) < 2:
        return KEYHOLDER_MARKS[0]
    
    # Join all but the last element with commas
    comma_separated = ", ".join(KEYHOLDER_MARKS[:-1])

    # Add "and" before the last element
    return f"{comma_separated} or {KEYHOLDER_MARKS[-1]}"

def get_shift_day_formatted(day_of_week, shift_date):
    """Get the shift date formatted with slack"""
    # convert date to datetime at noon, this will be the time zone of whever teh code is being run
    # which as long as its in the US will be fine since we are only displaying the date.
    date_time = datetime.combine(shift_date, datetime.min.time().replace(hour=12)) 

    formatted_date = f"<!date^{int(date_time.timestamp())}^{{date}}|{shift_date}>"

    if shift_date == date.today():
        return f"the shift *Today* ({formatted_date})"
    else:
        return f"the shift this *{day_of_week}* ({formatted_date})"

def send_volunteer_warning_message(day_of_week, shift_date, volunteers, has_keyholder):
    """
    Sends a warning message if the number of volunteers is below the VOLUNTEER threshold
    or if shift is missing a keyholder
    """
    message = f"For {get_shift_day_formatted(day_of_week, shift_date)}:\n"

    if len(volunteers) < VOLUNTEER_THRESHOLD:
    
        if len(volunteers) > 0:
            message += f"*•* We need more wrenches! There {'is' if len(volunteers) == 1 else 'are'} only {len(volunteers)} volunteers signed up! ({get_volunteer_list(volunteers)})\n"
        else:
            message += f"*•* We need more wrenches! No one has signed up :cry:\n"
            
        message += f"\t• *Sign up here: <{SHEET_URL}|Calender>*\n" # respectfully fuck slack for using this weird flavor of "markdown"
    if not has_keyholder:
        message += f"*•* We need a keyholder! (Remember to put {get_keyholder_marks_list()} after your name if are a keyholder)\n"

    channel = SHIFT_DAY_TO_CHANNEL[day_of_week]
        
    logging.info("sending message: " + message)
    send_message(channel, message)


def send_special_note_message(day_of_week, shift_date, special_notes):
    """Sends a message to a slack channel with any notes for the shift left in the calender"""
    message = f"For {get_shift_day_formatted(day_of_week, shift_date)} there are the following notes:\n"

    for special_note in special_notes:
        message += f"*•* {special_note}\n"
        
    channel = SHIFT_DAY_TO_CHANNEL[day_of_week]
        
    logging.info("sending message: " + message)
    send_message(channel, message)


#
#
# Start of calender_bot
#
#


def is_date(string):
    """Attempt to parse a string into a date object. Otherwise return None"""
    try:
        return parse(string).date()
    except ValueError:
        return None

def convert_dates(all_cells):
    """Convert date-like strings in a 2D list to date objects."""
    for row in range(len(all_cells)):
        for col in range(len(all_cells[row])):
            converted_date = is_date(all_cells[row][col])
            # check if successfully converted the cell to a date and update it
            if converted_date:
                all_cells[row][col] = converted_date

def get_date_location(date, all_cells):
    """
    Finds the row and column of the given date in the given cells using 0 based indexing
    Throws an error if the date is not found

    """
    for row_idx, row in enumerate(all_cells):
        for col_idx, value in enumerate(row):
            if value == date:
                return row_idx, col_idx  # Return the first occurrence
    raise ValueError(f"Date: {date} not found in the calender")

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

def get_voluneers_for_date(date, all_cells, worksheet):
    """
    Returns a tuple of two elements. The first is the list of volunteers for the shift. The second
    Is the list of special cells, like new volunteer that the shift may need to know about
    """
    # find the location of the given date in the worksheet
    row, col = get_date_location(date, all_cells)

    # increment the row by one to go one cell under the date
    row = row + 1

    all_volunteers = []
    special_rows = []

    # go down each row until the next date is reached or the end of the sheet is reached
    while type(all_cells[row][col]) is str and row < len(all_cells):
        cell = all_cells[row][col]

        # check if the cell is special or contains volunteer signup info
        if False: # is_special_cell(worksheet, row, col):
            special_rows.append(cell)
        else:
            # get volunteers names. The cell may contain multiple volunteers sigining up separated
            # by commas so split by commas and then remove any leading/trailing whitespace before
            # adding the volunteers to the volunteers list
            all_volunteers.extend(item.strip() for item in cell.split(","))

        # go down to the next cell
        row = row + 1

    # remove any possibly blank cells
    all_volunteers = [volunteer for volunteer in all_volunteers if volunteer.strip() not in (None, '')]
    special_rows = [special_row for special_row in special_rows if special_row.strip() not in (None, '')]

    return all_volunteers, special_rows

def get_has_keyholder(volunteers):
    return any(keyholder_mark in volunteer.lower() for keyholder_mark in KEYHOLDER_MARKS for volunteer in volunteers)

def send_slack_messages():
    # initiate google sheets connection with api key
    api_key = os.getenv('google_api_key')
    gc = gspread.api_key(api_key)

    # identify the sheet to work with
    sh = gc.open_by_key(SHEET_ID)

    # get the first sheet as it appears on google sheets and assume it is the current years calender
    current_calender = sh.get_worksheet(0)

    # get the entire sheets as a 2D array
    all_cells = current_calender.get_all_values()

    # # converts any strings that are dates into date objects
    # # if a cell is not a date, leave as is
    convert_dates(all_cells)

    # volunteers, special_rows = get_voluneers_for_date(date.today() + timedelta(days=6), all_cells, current_calender)
    # has_keyholder = get_has_keyholder(volunteers)

    # print(volunteers, has_keyholder, special_rows)

    today = date.today()

    for days_out in SHIFT_VOLUNTEER_WARNING_DAYS:
        date_to_check = today + timedelta(days=days_out)
        day_of_week = DAYS_OF_WEEK[date_to_check.weekday()]

        if day_of_week in SHIFT_DAYS:
            volunteers, _ = get_voluneers_for_date(today + timedelta(days=days_out), all_cells, current_calender)
            has_keyholder = get_has_keyholder(volunteers)

            if len(volunteers) < VOLUNTEER_THRESHOLD or not has_keyholder:
                send_volunteer_warning_message(day_of_week, date_to_check, volunteers, has_keyholder)

    # for days_out in SHIFT_SPECIAL_NOTES_DAYS:
    #     date_to_check = today + timedelta(days=days_out)
    #     day_of_week = DAYS_OF_WEEK[date_to_check.weekday()]

    #     if day_of_week in SHIFT_DAYS:
    #         _, special_cells = get_voluneers_for_date(today + timedelta(days=days_out), all_cells, current_calender)

    #         if special_cells:
    #             send_special_note_message(day_of_week, date_to_check, special_cells)

@app.timer_trigger(schedule="*/30 * * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def calender_bot(myTimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function executed.')
    send_message('#bot-tester', 'test message')
    send_slack_messages()
