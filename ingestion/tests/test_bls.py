"""Tests for BLS ingestor."""

from ingestion.bls import BLSIngestor


def test_bls_ingestor_init():
    ingestor = BLSIngestor()
    assert ingestor.source_name == "bls_wages"
