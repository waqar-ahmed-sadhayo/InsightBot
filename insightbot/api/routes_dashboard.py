"""Dashboard/stats endpoints, backing both the frontend dashboard widget
and ad-hoc API consumption. `export` writes the same CSVs Tableau reads.

    GET  /api/dashboard/stats            -> aggregated JSON
    POST /api/dashboard/export           (admin) -> (re)writes data/exports/*.csv
"""
from __future__ import annotations

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from insightbot.api.auth import admin_required
from insightbot.dashboard.aggregate import compute_stats, export_all

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("/stats")
@jwt_required()
def stats():
    return jsonify(compute_stats())


@bp.post("/export")
@admin_required
def export():
    return jsonify(export_all())
