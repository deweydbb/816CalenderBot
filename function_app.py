import azure.functions as func
import logging
from datetime import date, timedelta
import urllib.parse
import json
import os

from calender_bot.calender_bot import send_slack_messages
from calender_bot.hide_rows import hide_rows
from calender_bot.slack_poll import create_poll, update_poll
from calender_bot.bike_stand_reports import send_slack_message_for_new_reports

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.timer_trigger(schedule="0 0 15 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False) 
def calender_bot(myTimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function executed.')
    send_slack_messages()


@app.route(route="http_trigger_bot", auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger_bot(req: func.HttpRequest) -> func.HttpResponse:
    """Function for testing purposes only. Used to debug and force runs on different days"""
    logging.info('Python HTTP trigger function processed a request.')

    delta = req.params.get('delta')

    if delta:
        today = date.today() + timedelta(days=int(delta))
        logging.info(today)
        send_slack_messages(today=today)
        return func.HttpResponse(f"Hello. Sending as if today was {today}")
    else:
        send_slack_messages()

    return func.HttpResponse(f"Hello. Sending as if today was today")

@app.timer_trigger(schedule=" 0 0 15 * * 0", arg_name="timer", run_on_startup=False, use_monitor=False)
def hide_calendar_rows(timer: func.TimerRequest) -> None:
    logging.info('Hid calendar rows begin execution')
    if os.getenv('do_hide_rows_on_schedule') == "True":
        hide_rows()

@app.route(route="http_trigger_hide_rows", auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger_hide_rows(req: func.HttpRequest) -> func.HttpResponse:
    """Function for testing purposes only. Used to debug and force runs on different days"""
    logging.info('Python HTTP trigger function attempting to hide rows')

    delta = req.params.get('delta')

    if delta:
        today = date.today() + timedelta(days=int(delta))
        logging.info(today)
        hide_rows(today=today)
        return func.HttpResponse(f"Hello. Hiding as if today was {today}")
    else:
        hide_rows()
        return func.HttpResponse(f"Hello. Hiding as if today was today")
    

@app.timer_trigger(schedule="0 0 15 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False) 
def bike_stand_reports(myTimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function executed.')
    send_slack_message_for_new_reports()


@app.route(route="http_trigger_bike_stand_reports", auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger_bike_stand_reports(req: func.HttpRequest) -> func.HttpResponse:
    """Function for testing purposes only. Used to debug and force runs on different days"""
    logging.info('Python HTTP trigger function processed a request.')

    send_slack_message_for_new_reports()

    return func.HttpResponse(f"Hello. Sending new bike stand reports to slack")


# @app.route(route="create_poll", auth_level=func.AuthLevel.ANONYMOUS)
# def create_poll_test(req: func.HttpRequest) -> func.HttpResponse:
#     """Function for testing purposed only. Used to manually create a poll"""
#     create_poll("test question", ["Yes", "No", "I can bring food"], notify_channel=True)

#     return func.HttpResponse(f"End of function")

# @app.route(route="handle_interaction", auth_level=func.AuthLevel.ANONYMOUS)
# def handle_interaction(req: func.HttpRequest) -> func.HttpResponse:
#     body = urllib.parse.unquote_plus(req.get_body().decode("utf-8"))

#     body_json = json.loads(body[len("payload="):])

#     update_poll(body_json)

#     return func.HttpResponse(body="", status_code=200)

