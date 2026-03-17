"""Bureau of Labor Statistics (BLS) API ingestor.

Pulls wage and employment data by occupation and metro area.
API docs: https://www.bls.gov/bls/api_features.htm
"""

import os

import pandas as pd

from ingestion.base import BaseIngestor
from ingestion.utils import fetch_json

BLS_BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


class BLSIngestor(BaseIngestor):
    def __init__(self):
        super().__init__("bls_wages")
        self.api_key = os.getenv("BLS_API_KEY", "")

    def extract(self) -> pd.DataFrame:
        # TODO: Implement BLS API calls
        # - Pull Occupational Employment and Wage Statistics (OEWS)
        # - Series IDs follow pattern: OEUM{area}{industry}{occupation}{datatype}
        # - Need to batch requests (max 50 series per request)
        raise NotImplementedError("BLS ingestor not yet implemented")


if __name__ == "__main__":
    ingestor = BLSIngestor()
    ingestor.run()
