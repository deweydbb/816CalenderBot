import azure.functions as func
import logging

from calender_bot.calender_bot import send_slack_messages

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.timer_trigger(schedule="*/30 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False) 
def calender_bot(myTimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function executed.')
    send_slack_messages()
