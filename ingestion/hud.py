"""HUD (Housing and Urban Development) API ingestor.

Pulls fair market rents and housing affordability data.
API docs: https://www.hud.gov/program_offices/comm_planning/affordablehousing
"""

import os

import pandas as pd

from ingestion.base import BaseIngestor
from ingestion.utils import fetch_json

HUD_BASE_URL = "https://www.huduser.gov/hudapi/public"


class HUDIngestor(BaseIngestor):
    def __init__(self):
        super().__init__("hud_rents")
        self.api_token = os.getenv("HUD_API_TOKEN", "")

    def extract(self) -> pd.DataFrame:
        # TODO: Implement HUD API calls
        # - Fair Market Rents by metro/county
        # - Headers: {"Authorization": f"Bearer {self.api_token}"}
        # - Endpoints: /fmr/statedata, /fmr/data/{entityid}
        raise NotImplementedError("HUD ingestor not yet implemented")


if __name__ == "__main__":
    ingestor = HUDIngestor()
    ingestor.run()
