import azure.functions as func
import logging
from datetime import date, timedelta

from calender_bot.calender_bot import send_slack_messages

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.timer_trigger(schedule="0 0 9 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False) 
def calender_bot(myTimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function executed.')
    send_slack_messages()


@app.route(route="http_trigger_bot", auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger_bot(req: func.HttpRequest) -> func.HttpResponse:
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
