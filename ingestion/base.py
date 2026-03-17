"""Abstract base class for all data source ingestors."""

import logging
import os
from abc import ABC, abstractmethod

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class BaseIngestor(ABC):
    """Each data source implements extract() to pull from its API.

    Usage:
        class BLSIngestor(BaseIngestor):
            def extract(self) -> pd.DataFrame:
                # call BLS API, return DataFrame
                ...

        ingestor = BLSIngestor("bls_wages")
        ingestor.run()
    """

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.conn = self._get_connection()

    def _get_connection(self):
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "data_warehouse"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
        )

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """Pull data from the source API and return a clean DataFrame."""
        ...

    def load(self, df: pd.DataFrame, table_name: str) -> None:
        """Load a DataFrame into the raw schema using pandas + psycopg2."""
        from sqlalchemy import create_engine

        db_url = (
            f"postgresql://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', 'postgres')}"
            f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
            f"/{os.getenv('DB_NAME', 'data_warehouse')}"
        )
        engine = create_engine(db_url)
        df.to_sql(table_name, engine, schema="raw", if_exists="replace", index=False)
        logger.info(f"Loaded {len(df)} rows into raw.{table_name}")

    def run(self) -> None:
        """Execute the full extract → load pipeline."""
        logger.info(f"Starting ingestion: {self.source_name}")
        df = self.extract()
        logger.info(f"Extracted {len(df)} rows from {self.source_name}")
        self.load(df, self.source_name)
        logger.info(f"Completed ingestion: {self.source_name}")
