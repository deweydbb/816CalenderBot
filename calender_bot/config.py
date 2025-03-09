import os
import json
import logging

# do not change (for internal use of the program to map numbers to days)
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_config_from_environment(key_name, default=None):
    value = os.getenv(key_name)
    if value == None:
        if default != None:
            return default
        raise Exception(f"Environment Variable {key_name} is required")

    return value

### START OF CONFIG ###

# Can find in the URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/
SHEET_ID = get_config_from_environment('SHEET_ID')
# must be of the form https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit
SHEET_URL=f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

# text people can put after their name to indicate to the bot they are keyholder
KEYHOLDER_MARKS = json.loads(get_config_from_environment('KEYHOLDER_MARKS', default='["🔑"]'))

# Days where the shop is open
SHIFT_DAYS = json.loads(get_config_from_environment('SHIFT_DAYS', default='["Monday", "Thursday", "Saturday"]'))
# day of the week mapped to the slack channel to send the message in
# channel format is #{name of channel}
SHIFT_DAY_TO_CHANNEL = json.loads(get_config_from_environment('SHIFT_DAY_TO_CHANNEL', default='{"Monday": "#bot-tester", "Thursday": "#bot-tester", "Saturday": "#bot-tester"}'))
if set(SHIFT_DAY_TO_CHANNEL.keys()) != set(SHIFT_DAYS):
    raise KeyError("SHIFT_DAYS and SHIFT_DAY_TO_CHANNEL must have the same days") 


# How many days out should the low volunteer warning and no keyholder warning be sent 
SHIFT_VOLUNTEER_WARNING_DAYS = json.loads(get_config_from_environment('SHIFT_VOLUNTEER_WARNING_DAYS', '[6, 3, 0]'))
# How many days out should the special notes for shift be sent out. 
SHIFT_SPECIAL_NOTES_DAYS = json.loads(get_config_from_environment('SHIFT_SPECIAL_NOTES_DAYS', '[0]'))

# if under number of volunteers signed up for shift, send warning
VOLUNTEER_THRESHOLD = int(get_config_from_environment('VOLUNTEER_THRESHOLD', default='3'))

logging.info(
    f"KEYHOLDER_MARKS: {KEYHOLDER_MARKS}\n"
    f"SHIFT_DAYS: {SHIFT_DAYS}\n" 
    f"SHIFT_DAY_TO_CHANNEL: {SHIFT_DAY_TO_CHANNEL}\n" 
    f"SHIFT_VOLUNTEER_WARNING_DAYS: {SHIFT_VOLUNTEER_WARNING_DAYS}\n"
    f"VOLUNTEER_THRESHOLD: {VOLUNTEER_THRESHOLD}\n"
)