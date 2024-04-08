import random

import gspread
from oauth2client.service_account import ServiceAccountCredentials

class Gsheets:
    runs = 0
    sheetname = ""
    def __init__(self, secret_path, sheetname):
        self.client = self._connect(secret_path)
        self.sheetname = sheetname

    def _connect(self, secret_path):
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(secret_path, scope)
        client = gspread.authorize(creds)
        return client

    def fetchfromsheets(self, worksheetname):
        sheet = self.client.open(self.sheetname)
        result = sheet.worksheet(worksheetname).get_all_records()
        return result

    def add_score(self, row):
        sheet = self.client.open(self.sheetname)
        if self.runs == 0:
            self.runs = len(sheet.worksheet("RUNS").col_values(1))
        self.runs += 1
        sheet.worksheet("RUNS").update(f'A{self.runs}:H{self.runs}', [row])







