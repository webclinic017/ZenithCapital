import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import *

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def get_points_and_settings():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "cred.json", SCOPES)
            creds = flow.run_local_server(port=12345)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
      points = {}
      settings = {}
      service = build("sheets", "v4", credentials=creds)
      
      sheet_service = service.spreadsheets()
      result = sheet_service.get(spreadsheetId=SPREADSHEET_ID).execute()
      sheets = result.get("sheets", "")
        
      for sheet in sheets:
        points[sheet["properties"]["title"]] = []
        current_sheet = sheet_service.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet["properties"]["title"] + "!A:H").execute()
        values = current_sheet.get("values", [])
        for value in values[1:]:
          level = float(value[0].replace(",", ""))
          support_success = float(value[-2].replace("%", "")) / 100
          resistance_success = float(value[-1].replace("%", "")) / 100
          points[sheet["properties"]["title"]].append([level, support_success, resistance_success])
          
        current_sheet = sheet_service.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet["properties"]["title"] + "!J2:K2").execute()
        values = current_sheet.get("values", [])
        
        minimum_probability = float(values[0][0].replace("%", "")) / 100
        enabled = values[0][1] == "TRUE"
      
        settings[sheet.get("properties", {}).get("title", "")] = {
          "minimum_probability": minimum_probability, 
          "enabled": enabled
        }
        
      return points, settings
 
    except HttpError as err:
      print(err)
      return None


if __name__ == "__main__":
  points, settings = get_points_and_settings()
  print(points)
  print(settings)