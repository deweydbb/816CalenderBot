import requests
from pprint import pprint
import traceback

from calender_bot.slack import send_message
from calender_bot.config import get_config_from_environment

import logging

from datetime import datetime
from zoneinfo import ZoneInfo

# Survey123 URL Info
# I am going to do my best to document everything I have figured out about the url format so that if things change you are able to figure things out
#
# Survey link: https://survey123.arcgis.com/share/<SURVEY_ID>
#
# Survey Results Dashboard: https://survey123.arcgis.com/share/<SURVEY_ID>/result
#   - This should take you to a dashboard that allows you to see aggregated responses over some time period
#
# The next thing to figure out is the organization id. This can be found by going to the `/result` dashboard,
# inspecting element and then going to the network tab and then refreshing the page. You will see a lot of network
# requests. You care about network requests with the following url format:
# https://services.arcgis.com/<ORG_ID>/arcgis/rest/services/survey123_<SURVEY_ID>_results/FeatureServer/0/...
# you can add ?f=json to the end of the url to get the raw data
#
#
# To get use information about a survey, go to the following url (as in enter this url into your browser):
# https://services.arcgis.com/<ORG_ID>/arcgis/rest/services/survey123_<SURVEY_ID>_results/FeatureServer/0
#
# The most important info is the fields section which should tell you the names of the fields asked in the survey.
# I think this is the documentation link: https://developers.arcgis.com/rest/services-reference/enterprise/layer-feature-service/
# for the above url.
#
# To query for results, I use the url format:
# https://services.arcgis.com/<ORG_ID>/arcgis/rest/services/survey123_<SURVEY_ID>_results/FeatureServer/0/query
# documentation: https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/
#
# To get the attachments related to a specific survey response, the url format is:
# https://services.arcgis.com/<ORG_ID>/arcgis/rest/services/survey123_<SURVEY_ID>_results/FeatureServer/0/<OBJECT_ID>/attachments
# where <OBJECT_ID> is the "objectid" field from an individual response
# documentation: https://developers.arcgis.com/rest/services-reference/enterprise/attachment-infos-feature-service/
#
# For attachment urls (photos, files, etc uploaded by the user in the survey), the link format to the resource is:
# https://services.arcgis.com/<ORG_ID>/arcgis/rest/services/survey123_<SURVEY_ID>_results/FeatureServer/0/<OBJECT_ID>/attachments/<attachmentId>
# where the attachment id comes from the above api call.
# documentation: https://developers.arcgis.com/rest/services-reference/enterprise/attachment-feature-service/
#
# Finally, the url format to view a specific response is:
# https://survey123.arcgis.com/share/<SURVEY_ID>?mode=view&globalId=<GLOBAL_ID>
# where global id comes from a specific response.
# documentation: https://doc.arcgis.com/en/survey123/get-started/integrate-launchwebapp.htm


def get_new_bike_reports():
    ORG_ID = get_config_from_environment("ORG_ID")
    SURVEY_ID = get_config_from_environment("SURVEY_ID")
    FEATURE_URL = f"https://services.arcgis.com/{ORG_ID}/arcgis/rest/services/survey123_{SURVEY_ID}_results/FeatureServer/0"

    # Query new features
    params = {
        "where": f"CreationDate >= CURRENT_TIMESTAMP - INTERVAL '1' DAY",
        "outFields": "CreationDate,Creator,additional_details,email,field_2,name,objectid,what_is_the_problem,what_is_the_problem_other,globalid",
        "f": "json",
        "returnGeometry": "false",
        "resultRecordCount": 2000
    }

    resp = requests.get(FEATURE_URL + "/query", params=params).json()

    logging.info(f"query reports in last day: {resp}")

    features = resp.get("features", [])

    reports = []

    for feat in features:
        oid = feat["attributes"]["objectid"]

        # Get list of attachments
        attach_url = f"{FEATURE_URL}/{oid}/attachments"
        attachments = requests.get(attach_url, params={"f": "json"}).json()

        attachment_urls = []

        for att in attachments.get("attachmentInfos", []):
            att_id = att["id"]
            attachment_urls.append(f"{attach_url}/{att_id}")

        problems = []

        if feat["attributes"]["what_is_the_problem"] is not None:
            problems = feat["attributes"]["what_is_the_problem"].split(',')
        # what_is_the_problem_other captures the text response if the user selects other for the problem
        if feat["attributes"]["what_is_the_problem_other"] is not None:
            problems.append(feat["attributes"]["what_is_the_problem_other"])

        globalId = feat["attributes"]["globalid"]
        viewUrl = f"https://survey123.arcgis.com/share/{SURVEY_ID}?mode=view&globalId={globalId}"

        reports.append({
            "DateReported": feat["attributes"]["CreationDate"],
            "ReporterName": feat["attributes"]["name"],
            "ReporterEmail": feat["attributes"]["email"],
            "StandLocation": feat["attributes"]["field_2"],
            "problems": problems,
            "additionalDetails": feat["attributes"]["additional_details"],
            "attachments": attachment_urls,
            "viewUrl": viewUrl
        })

    return reports

def get_reported_date(report):
    report_millis = report['DateReported']

    report_secs = int(report_millis / 1000)

    dt_utc = datetime.fromtimestamp(report_secs)
    dt_central = dt_utc.astimezone(ZoneInfo("America/Chicago"))

    fallback = dt_central.strftime("%Y-%m-%d %I:%M:%S %p %Z")

    return f"<!date^{report_secs}^{{date_short}} at {{time}}|{fallback}>"

def get_reporter_details(report):
    reporter_name = report['ReporterName']
    reporter_email = report['ReporterEmail']

    if reporter_name is None and reporter_email is None:
        return None

    if reporter_name is None and reporter_email is not None:
        return reporter_email

    if reporter_name is not None and reporter_email is None:
        return reporter_name

    return f"{reporter_name} ({reporter_email})"

def send_slack_message_for_new_reports():
    try:
        reports = get_new_bike_reports()

        logging.info(f"reports = {reports}")

        for report in reports:
            message = f"New <{report['viewUrl']}|Report> for {report['StandLocation']} Maintenance Stand\n"

            message += f"*•* Reported on {get_reported_date(report)}:\n"

            message += '*•* Problems:\n'

            for problem in report['problems']:
                message += f"\t*•* {problem}\n"

            additional_details = report['additionalDetails']
            if additional_details is not None:
                message += f"*•* Additional Details: {additional_details}\n"

            reporter = get_reporter_details(report)
            if reporter is not None:
                message += f"*•* Reporter: {reporter}\n"

            attachments = report['attachments']
            if len(attachments) > 0:
                formatted_urls = ", ".join(f"<{url}|Photo>" for url in attachments)
                message += f"*•* {formatted_urls}"

            logging.info("sending bike report message in slack: " + message)

            channel = get_config_from_environment("BIKE_STAND_CHANNEL")

            send_message(channel, message)
    except Exception as e:
        # if failed to run send a message to the bot tester so someone is aware of the failure 
        stack_trace = traceback.format_exc()
        error_msg = "Bot encountered error sending bike stand report messages. Error: " + str(e) + " Stack trace: " + stack_trace
        logging.error(error_msg)
        
        send_message("#bot-tester", error_msg)

        raise e