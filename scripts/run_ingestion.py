"""Orchestrator — run all or selected data source ingestors."""

import argparse
import logging

from ingestion.bls import BLSIngestor
from ingestion.census import CensusIngestor
from ingestion.fbi_crime import FBICrimeIngestor
from ingestion.hud import HUDIngestor
from ingestion.numbeo import NumbeoIngestor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

INGESTORS = {
    "bls": BLSIngestor,
    "census": CensusIngestor,
    "hud": HUDIngestor,
    "fbi": FBICrimeIngestor,
    "numbeo": NumbeoIngestor,
}


def main():
    parser = argparse.ArgumentParser(description="Run data ingestion pipelines")
    parser.add_argument("--source", type=str, help="Single source to run (bls, census, hud, fbi, numbeo)")
    parser.add_argument("--all", action="store_true", help="Run all ingestors")
    args = parser.parse_args()

    if args.all:
        sources = list(INGESTORS.keys())
    elif args.source:
        sources = [args.source]
    else:
        parser.print_help()
        return

    for source in sources:
        if source not in INGESTORS:
            logger.error(f"Unknown source: {source}. Available: {list(INGESTORS.keys())}")
            continue
        try:
            ingestor = INGESTORS[source]()
            ingestor.run()
        except NotImplementedError:
            logger.warning(f"Skipping {source} — not yet implemented")
        except Exception as e:
            logger.error(f"Failed to ingest {source}: {e}")


if __name__ == "__main__":
    main()
