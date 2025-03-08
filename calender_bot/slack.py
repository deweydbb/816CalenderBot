import os
import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, date

from calender_bot.config import * # yeah this is kinda awful but I don't feel like improving it with a real config file

def send_message(channel_id, message):
    slack_token = os.getenv('slack_token')
    client = WebClient(token=slack_token)

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