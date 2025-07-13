import os
import json
import logging
import time
import traceback
import requests
from dataclasses import dataclass, field
from typing import List, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from pprint import pprint

# do not change (for internal use of the program to map numbers to days)
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_config_from_environment(key_name, default=None):
    value = os.getenv(key_name)
    if value == None:
        if default != None:
            return default
        raise Exception(f"Environment Variable {key_name} is required")

    return value

@dataclass
class MessageConfig:
    days: List[str]
    days_before: int
    notify_channel: bool
    volunteer_threshold: int = 4
    channel: str = "#bot-tester"
    notify_keyholders: bool = False
    keyholder_marks: List[str] = field(default_factory=lambda: ["🔑"])
    bikeschool_marks: List[str] = field(default_factory=lambda: ["skool", "school"])
    

    def get_keyholder_marks_list(self):
        if len(self.keyholder_marks) < 2:
            return self.keyholder_marks[0]
        
        # Join all but the last element with commas
        comma_separated = ", ".join(self.keyholder_marks[:-1])

        # Add "and" before the last element
        return f"{comma_separated} or {self.keyholder_marks[-1]}"


@dataclass
class Config:
    shift_warning: List[MessageConfig]
    shift_notes: List[MessageConfig]
    bike_school_reminder: List[MessageConfig]

def get_config_fallback() -> Config:
    with open("./calender_bot/config.json", "r") as file:
        raw_config = os.getenv("calender_bot_config")
        data_dict = None
        if raw_config:
            data_dict = json.loads(raw_config)
        else:
            data_dict = json.load(file)

        shift_warning = [MessageConfig(**msg_config) for msg_config in data_dict['shift_warning']]
        shift_notes = [MessageConfig(**msg_config) for msg_config in data_dict['shift_notes']]
        bike_school_reminder = [MessageConfig(**msg_config) for msg_config in data_dict['bike_school_reminder']]

        return Config(shift_warning=shift_warning, shift_notes=shift_notes, bike_school_reminder=bike_school_reminder)
    raise Exception("Failed to open file and get config")

#
# START OF GET CONFIG CODE FROM GOOGLE SHPREADSHEET
#

# some code had to be repeated to avoid circular imports
def _send_message_internal(channel_id, message, use_blocks, fallback_text):
    slack_token = os.getenv('slack_token')
    client = WebClient(token=slack_token)

    if use_blocks:
        return client.chat_postMessage(
            channel=channel_id,
            text=fallback_text,
            blocks=message
        )
    
    return client.chat_postMessage(
        channel=channel_id,
        text=message,
    )

def send_message(channel_id, message, use_blocks=False, fallback_text=None):
    """Send the given message to the specified channel and respect rate limits"""
    try:
        # Sending a message to the specified Slack channel
        _send_message_internal(channel_id, message, use_blocks, fallback_text)
        logging.info(f"Message sent successfully")
    except SlackApiError as e:
        if e.response.status_code == 429:
            # The `Retry-After` header will tell you how long to wait before retrying
            delay = int(e.response.headers['Retry-After'])
            print(f"Rate limited. Retrying in {delay} seconds")
            time.sleep(delay)
            _send_message_internal(channel_id, message, use_blocks, fallback_text)
        else:
            logging.error(f"Error sending message: {e}")

def get_row_and_column_count(sheets, gid):
    for sheet in sheets:
        if str(sheet['properties']['sheetId']) == str(gid):
            gridProps = sheet['properties']['gridProperties']
            return sheet['properties']['title'], gridProps['rowCount'], gridProps['columnCount']
    raise Exception("Sheet GID not found: " + str(gid) + str(sheets))
        
## shamelessly stolen from gspread
def rowcol_to_a1(row: int, col: int) -> str:
    """Translates a row and column cell address to A1 notation.

    :param row: The row of the cell to be converted.
        Rows start at index 1.
    :type row: int, str

    :param col: The column of the cell to be converted.
        Columns start at index 1.
    :type row: int, str

    :returns: a string containing the cell's coordinates in A1 notation.

    Example:

    >>> rowcol_to_a1(1, 1)
    A1

    """

    div = col
    column_label = ""

    while div:
        (div, mod) = divmod(div, 26)
        if mod == 0:
            mod = 26
            div -= 1
        column_label = chr(mod + 64) + column_label

    label = "{}{}".format(column_label, row)

    return label

# returns the range of all the sheets values in A1 format
def get_entire_sheet_range(sheet_title, num_rows, num_cols):
    return f"{sheet_title}!A1:{rowcol_to_a1(num_rows, num_cols)}"

def get_sheet_row_data(sheets, gid):
    for sheet in sheets:
        if str(sheet['properties']['sheetId']) == str(gid):
            return sheet['data'][0]['rowData']
    raise Exception("Sheet GID not found: " + str(gid))


def get_sheet_data(sheet_id, gid):
    api_key = os.getenv('google_api_key')

    base_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
    key_param = f"key={api_key}"
    # what fields to return from the api
    field_mask = "fields=sheets.properties(title,sheetId,gridProperties(rowCount,columnCount))"

    r = requests.get(f"{base_url}?{key_param}&{field_mask}")

    sheets = r.json()['sheets']

    sheet_title, num_rows, num_cols = get_row_and_column_count(sheets, gid)

    sheet_range = get_entire_sheet_range(sheet_title, num_rows, num_cols)

    # what fields to return from the third api call
    field_mask = "fields=sheets(properties.sheetId,data.rowData.values.formattedValue)"
    r = requests.get(f"{base_url}?{key_param}&ranges={sheet_range}&{field_mask}")

    row_data = get_sheet_row_data(r.json()['sheets'], gid)

    data = []

    for row in row_data:
        new_row = []

        if 'values' in row:
            for cell in row['values']:
                value = cell['formattedValue'] if 'formattedValue' in cell else ''

                new_row.append(value)

        data.append(new_row)

    return data

def get_day_index(day_text):
    day_index = DAYS_OF_WEEK.index(day_text)
    if day_index == -1:
        raise Exception("Shift day not recognized, must be one of " + DAYS_OF_WEEK)
    return day_index

def get_days_before(target_day, day_to_send):
    if day_to_send <= target_day:
        return target_day - day_to_send
    else:
        return target_day + len(DAYS_OF_WEEK) - day_to_send

def get_config_locations(data):
    config_locations = []

    for rowIdx, row in enumerate(data):
        for colIdx, cell in enumerate(row):
            if cell.startswith("Shift: ") or cell.startswith('Bike School Reminder: '):
                configType = "shift" if cell.startswith("Shift: ") else "bike school"
                dayIndex = get_day_index(cell.split(": ", 1)[1])
                
                config_locations.append({
                    "type": configType,
                    "day": dayIndex,
                    "row": rowIdx + 1, # increment by one to get to first row of config data
                    "col": colIdx + 1 # increment by one to get to frist column of config data
                })
    return config_locations

def get_shift_warnings_from_location(data, config_location):
    row_start = config_location['row']
    col_start = config_location['col']
    target_day_index = config_location['day']
    target_day = DAYS_OF_WEEK[target_day_index]

    shift_warnings = []

    for col in range(col_start, col_start + len(DAYS_OF_WEEK), 1):
        if data[row_start + 1][col] == 'TRUE':
            day_to_send_index = get_day_index(data[row_start][col]) 

            days_before = get_days_before(target_day_index, day_to_send_index)
            notify_channel = data[row_start + 2][col] == 'TRUE'
            channel = data[row_start + 3][col]
            volunteer_threshold = int(data[row_start + 4][col])

            shift_warnings.append(MessageConfig([target_day], days_before, notify_channel, volunteer_threshold=volunteer_threshold, channel=channel))

    return shift_warnings

def get_shift_notes_from_location(data, config_location):
    row_start = config_location['row']
    col_start = config_location['col']
    target_day_index = config_location['day']
    target_day = DAYS_OF_WEEK[target_day_index]

    shift_notes = []

    for col in range(col_start, col_start + len(DAYS_OF_WEEK), 1):
        if data[row_start + 6][col] == 'TRUE':
            day_to_send_index = get_day_index(data[row_start][col]) 

            days_before = get_days_before(target_day_index, day_to_send_index)
            channel = data[row_start + 7][col]

            shift_notes.append(MessageConfig([target_day], days_before, False, channel=channel))

    return shift_notes

def get_bike_school_reminders_from_location(data, config_location):
    row_start = config_location['row']
    col_start = config_location['col']
    target_day_index = config_location['day']
    target_day = DAYS_OF_WEEK[target_day_index]

    bike_reminders = []

    for col in range(col_start, col_start + len(DAYS_OF_WEEK), 1):
        if data[row_start + 1][col] == 'TRUE':
            day_to_send_index = get_day_index(data[row_start][col]) 

            days_before = get_days_before(target_day_index, day_to_send_index)
            notify_channel = data[row_start + 2][col] == 'TRUE'
            channel = data[row_start + 3][col]

            bike_reminders.append(MessageConfig([target_day], days_before, notify_channel, channel=channel))

    return bike_reminders

def update_config(config, data, config_location):
    if config_location['type'] == 'shift':
        config.shift_warning.extend(get_shift_warnings_from_location(data, config_location))
        config.shift_notes.extend(get_shift_notes_from_location(data, config_location))
    elif config_location['type'] == 'bike school':
        config.bike_school_reminder.extend(get_bike_school_reminders_from_location(data, config_location))


def get_config() -> Config:
    try:
        configSheetId = get_config_from_environment('CONFIG_SHEET_ID')
        configSheetGid = get_config_from_environment('CONFIG_SHEET_GID')

        data = get_sheet_data(configSheetId, configSheetGid)

        config_locations = get_config_locations(data)
        config = Config([], [], [])

        for config_location in config_locations:
            update_config(config, data, config_location)

        # pprint(config)
        return config
    except Exception as e:
        # if failed to get config from google sheet, fall back to default config and send message
        # to slack so we are aware the google sheet config is broken
        stack_trace = traceback.format_exc()
        error_msg = "Bot encountered error parsing google sheet config. Falling back to default config. Error: " + str(e) + " Stack trace: " + stack_trace
        logging.info(error_msg)
        
        send_message("#bot-tester", error_msg)
        
        return get_config_fallback()        

# Can find in the URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/
SHEET_ID = get_config_from_environment('SHEET_ID')
# must be of the form https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit
SHEET_URL=f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
