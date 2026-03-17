"""US Census Bureau API ingestor.

Pulls median home values, rents, income, demographics from ACS.
API docs: https://www.census.gov/data/developers/data-sets.html
"""

import os

import pandas as pd

from ingestion.base import BaseIngestor
from ingestion.utils import fetch_json

CENSUS_BASE_URL = "https://api.census.gov/data"


class CensusIngestor(BaseIngestor):
    def __init__(self):
        super().__init__("census_acs")
        self.api_key = os.getenv("CENSUS_API_KEY", "")

    def extract(self) -> pd.DataFrame:
        # TODO: Implement Census ACS API calls
        # - American Community Survey 5-Year Estimates
        # - Variables: B25077_001E (median home value), B25064_001E (median rent),
        #   B19013_001E (median household income), B01003_001E (population)
        # - Geography: county level or place level
        raise NotImplementedError("Census ingestor not yet implemented")


if __name__ == "__main__":
    ingestor = CensusIngestor()
    ingestor.run()
