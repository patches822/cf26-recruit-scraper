import csv
import os
import gspread
import logging
from abc import ABC, abstractmethod
from config import BASIC_INFO_HEADERS, ATTRIBUTE_HEADERS
from oauth2client.service_account import ServiceAccountCredentials
from src.models import Recruit

logger = logging.getLogger(__name__)

class OutputManager(ABC):
    """Abstract Base Class defining the contract for all storage types."""
    
    @abstractmethod
    def save(self, recruit: Recruit):
        pass

class CSVManager(OutputManager):
    """Handles local storage in a CSV file."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(BASIC_INFO_HEADERS + ATTRIBUTE_HEADERS)

    def save(self, recruit: Recruit):
        with open(self.filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(recruit.to_row())

class SheetsManager(OutputManager):
    """Handles live syncing with Google Sheets."""
    
    def __init__(self, sheet_name: str, creds_file: str):
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)
        self.sheet = client.open(sheet_name).sheet1
        logger.info("Connected to Google Sheets successfully.")

    def save(self, recruit: Recruit):
        self.sheet.append_row(recruit.to_row())