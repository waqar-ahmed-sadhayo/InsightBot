"""Ingestion layer: fetch raw HTML for configured sites and persist it
(with metadata) to disk before any parsing happens, so extraction can be
re-run/re-tuned without re-fetching the network.
"""
