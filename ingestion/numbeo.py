"""Numbeo API ingestor.

Pulls cost of living indexes and quality of life scores.
API docs: https://www.numbeo.com/common/api.jsp
"""

import os

import pandas as pd

from ingestion.base import BaseIngestor
from ingestion.utils import fetch_json

NUMBEO_BASE_URL = "https://www.numbeo.com/api"


class NumbeoIngestor(BaseIngestor):
    def __init__(self):
        super().__init__("numbeo_col")
        self.api_key = os.getenv("NUMBEO_API_KEY", "")

    def extract(self) -> pd.DataFrame:
        # TODO: Implement Numbeo API calls
        # - Endpoints: /city_cost_of_living, /city_quality_of_life
        # - Params: api_key, query (city name), country (United States)
        # - Note: Free tier may have limited access — may need paid tier
        raise NotImplementedError("Numbeo ingestor not yet implemented")


if __name__ == "__main__":
    ingestor = NumbeoIngestor()
    ingestor.run()
