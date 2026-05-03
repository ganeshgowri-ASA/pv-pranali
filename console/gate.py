#!/usr/bin/env python3
"""Gate approval CLI for pv-pranali pipeline runs.

Usage:
    python console/gate.py list
    python console/gate.py approve <run_id>
    python console/gate.py reject <run_id> --reason "needs re-check"
    python console/gate.py status <run_id>

Requires env vars: SUPABASE_URL, SUPABASE_KEY
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

import typer
from supabase import create_client, Client

app = typer.Typer(help="pv-pranali gate approval console")


def _client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        typer.echo("Error: SUPABASE_URL and SUPABASE_KEY must be set.", err=True)
        raise typer.Exit(1)
    return create_client(url, key)


@app.command()
def list():
    """Show all pending gate events across all runs."""
    db = _client()
    rows = (
        db.table("gate_events")
        .select("id, run_id, gate_name, status, created_at")
        .eq("status", "pending")
        .order("created_at")
        .execute()
        .data
    )
    if not rows:
        typer.echo("No pending gates.")
        return
    typer.echo(f"{'ID':<36}  {'RUN_ID':<36}  {'GATE':<20}  SINCE")
    typer.echo("-" * 110)
    for r in rows:
        typer.echo(
            f"{r['id']:<36}  {r['run_id']:<36}  {r['gate_name']:<20}  {r['created_at']}"
        )


@app.command()
def approve(
    run_id: str = typer.Argument(..., help="pipeline_run UUID to approve"),
):
    """Approve the pending gate for a run."""
    db = _client()
    result = (
        db.table("gate_events")
        .update({
            "status": "approved",
            "decided_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("run_id", run_id)
        .eq("status", "pending")
        .execute()
    )
    updated = len(result.data)
    if updated == 0:
        typer.echo(f"No pending gate found for run {run_id}.", err=True)
        raise typer.Exit(1)
    typer.echo(f"Approved {updated} gate(s) for run {run_id}.")


@app.command()
def reject(
    run_id: str = typer.Argument(..., help="pipeline_run UUID to reject"),
    reason: str = typer.Option(..., "--reason", "-r", help="Reason for rejection"),
):
    """Reject the pending gate for a run."""
    db = _client()
    result = (
        db.table("gate_events")
        .update({
            "status": "rejected",
            "reason": reason,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("run_id", run_id)
        .eq("status", "pending")
        .execute()
    )
    updated = len(result.data)
    if updated == 0:
        typer.echo(f"No pending gate found for run {run_id}.", err=True)
        raise typer.Exit(1)
    typer.echo(f"Rejected {updated} gate(s) for run {run_id}. Reason: {reason}")


@app.command()
def status(
    run_id: str = typer.Argument(..., help="pipeline_run UUID to inspect"),
):
    """Show all gate events for a run."""
    db = _client()
    rows = (
        db.table("gate_events")
        .select("id, gate_name, status, reason, decided_at, created_at")
        .eq("run_id", run_id)
        .order("created_at")
        .execute()
        .data
    )
    if not rows:
        typer.echo(f"No gate events found for run {run_id}.")
        return
    typer.echo(f"Gates for run {run_id}:")
    typer.echo(f"  {'GATE':<20}  {'STATUS':<10}  {'DECIDED':<27}  REASON")
    typer.echo("  " + "-" * 80)
    for r in rows:
        decided = r.get("decided_at") or "—"
        reason = r.get("reason") or ""
        typer.echo(
            f"  {r['gate_name']:<20}  {r['status']:<10}  {decided:<27}  {reason}"
        )


if __name__ == "__main__":
    app()
