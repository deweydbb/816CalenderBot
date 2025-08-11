import os
import requests
from dateutil.parser import parse
from datetime import date
import logging
import httplib2

from apiclient import discovery
from google.oauth2 import service_account

from calender_bot.calender_bot import get_default_sheet, get_cell_is_date
from calender_bot.config import *

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
def get_entire_sheet_range(num_rows, num_cols):
    return f"A1:{rowcol_to_a1(num_rows, num_cols)}"

def get_sheet_data(api_key, sheet_id):
    base_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
    key_param = f"key={api_key}"
    # what fields to return from the api
    field_mask = "fields=sheets.properties(index,sheetId,gridProperties(rowCount,columnCount,frozenRowCount))"
    r = requests.get(f"{base_url}?{key_param}&{field_mask}")

    sheets = r.json()['sheets']
    default_sheet = get_default_sheet(sheets)

    num_rows = default_sheet['properties']['gridProperties']['rowCount']
    num_cols = default_sheet['properties']['gridProperties']['columnCount']

    sheet_range = get_entire_sheet_range(num_rows, num_cols)

    # what fields to return from the third api call
    field_mask = "fields=sheets.data(rowMetadata.hiddenByUser,rowData.values(effectiveFormat(numberFormat,backgroundColor),formattedValue))"
    r = requests.get(f"{base_url}?{key_param}&ranges={sheet_range}&{field_mask}")

    response = r.json()

    row_data = response['sheets'][0]['data'][0]['rowData']
    row_metadata = response['sheets'][0]['data'][0]['rowMetadata']

    data = []

    for index, row in enumerate(row_data):
        is_row_hidden = row_metadata[index]['hiddenByUser'] if 'hiddenByUser' in row_metadata[index] else False

        new_row = {"hidden": is_row_hidden, "cells": []}

        for cell in row['values']:
            is_date = get_cell_is_date(cell)
            value = cell['formattedValue'] if 'formattedValue' in cell else ''
            # convert value to date if it is a date 
            if is_date and value:
                value = parse(value).date()

            new_row['cells'].append({"is_date": is_date, "value": value})

        data.append(new_row)

    return default_sheet, data

def get_date_location(date, data):
    """
    Finds the row and column of the given date in the given cells using 0 based indexing
    Throws an error if the date is not found
    """
    for row_idx, row in enumerate(data):
        for col_idx, cell in enumerate(row['cells']):
            if cell['value'] == date:
                return row_idx, col_idx  # Return the first occurrence
    raise ValueError(f"Date: {date} not found in the calender")

def get_first_non_hidden_row(data, frozen_row_count):
    for row_index, row in enumerate(data):
        # return first row that is not hidden and is not frozen (pinned)
        if not row['hidden'] and row_index >= frozen_row_count:
            return row_index

    return len(data)

def do_hide_rows_api_call(credentials, spreadsheet_id, sheet_id, start_row, end_row):
    """
    Hides the given range of rows [start_row, end_row) (inclusive on start, exclusive on end)
    rows are specified using zero based indexing
    """
    service = discovery.build('sheets', 'v4', credentials=credentials)

    body = {
        "requests": [{
            "updateDimensionProperties": {
                "properties": {
                    "hiddenByUser": True
                },
                "fields": "hiddenByUser",
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start_row,
                    "endIndex": end_row,
                }
            }
        }],
        "includeSpreadsheetInResponse": False,
    }

    r = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body
    ).execute()

    logging.info(r)

def hide_rows(today = date.today()):
    """
    Hides all rows up until (but not including) the row containing the given date
    Does not hide frozen (pinned) rows
    """

    google_api_key = os.getenv('google_api_key')

    default_sheet, data = get_sheet_data(google_api_key, SHEET_ID)

    # get the index of the row containing todays date
    today_row_index, _ = get_date_location(today, data)

    
    frozen_row_count = default_sheet['properties']['gridProperties']['frozenRowCount']
    # get first unhidden row that is not frozen (pinned)
    first_non_hidden_row_index = get_first_non_hidden_row(data, frozen_row_count)

    # hid all nonforzen rows up until the row before todays date
    if (first_non_hidden_row_index < today_row_index):
        logging.info(f"hiding rows {first_non_hidden_row_index} to {today_row_index}")
        scopes = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/spreadsheets"]
        google_service_account_private_key = json.loads(os.getenv('google_service_account'))

        # have to use a service account credentials (2 legged oauth) to make modifications
        # to a sheet instead of just using an api key
        credentials = service_account.Credentials.from_service_account_info(google_service_account_private_key, scopes=scopes)

        default_sheet_id = default_sheet['properties']['sheetId']
        # SHEET_ID is technically the spreadsheet id, and default_sheet_id is the actual sheet id to modify
        do_hide_rows_api_call(credentials, SHEET_ID, default_sheet_id, first_non_hidden_row_index, today_row_index)
    else:
        logging.info("no rows to hide")