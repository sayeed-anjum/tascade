"""Thin command-line client for the Tascade REST API.

This package talks to Tascade over HTTP only. It must never import the store
or the FastAPI app: see docs/design/2026-09-08-control-plane-for-herdr-agents.md
decision D2.
"""
