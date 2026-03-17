"""FBI Crime Data Explorer API ingestor.

Pulls crime statistics by city and region.
API docs: https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi
"""

import os

import pandas as pd

from ingestion.base import BaseIngestor
from ingestion.utils import fetch_json

FBI_BASE_URL = "https://api.usa.gov/crime/fbi/sapi"


class FBICrimeIngestor(BaseIngestor):
    def __init__(self):
        super().__init__("fbi_crime")
        self.api_key = os.getenv("FBI_API_KEY", "")

    def extract(self) -> pd.DataFrame:
        # TODO: Implement FBI Crime Data API calls
        # - Endpoints: /api/estimates/national, /api/summarized/state/{stateAbbr}
        # - Note: UCR/NIBRS transition causes schema differences across years
        # - Need to handle both reporting formats
        raise NotImplementedError("FBI Crime ingestor not yet implemented")


if __name__ == "__main__":
    ingestor = FBICrimeIngestor()
    ingestor.run()
