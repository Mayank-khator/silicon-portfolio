#!/usr/bin/env python3
"""Explicitly provision synthetic data in a development Supabase project.

Requires SUPABASE_SERVICE_ROLE_KEY and SILICON_DEMO_PASSWORD in the environment.
No password or key is stored in the repository, printed, or returned in errors.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import UUID, uuid4, uuid5


class BootstrapError(Exception):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("SUPABASE_URL", "http://127.0.0.1:54321"))
    parser.add_argument("--email", required=True, help="Email for an explicitly provisioned development user")
    parser.add_argument("--user-id", type=UUID, help="Reuse an existing Auth user instead of creating one")
    parser.add_argument("--tenant-id", type=UUID, help="Reuse a previously provisioned synthetic tenant")
    parser.add_argument("--tenant-name", default="Helix Semiconductor · Synthetic demo")
    parser.add_argument("--allow-remote", action="store_true", help="Confirm this remote Supabase project is for nonproduction demo data")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    parsed = urlparse(base_url)
    is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise BootstrapError("SUPABASE_URL must be an HTTP(S) URL")
    if not is_local and (not args.allow_remote or parsed.scheme != "https"):
        raise BootstrapError("Remote seeding requires HTTPS and --allow-remote for a nonproduction project")
    if "@" not in args.email:
        raise BootstrapError("Provide a valid development email address")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not service_key:
        raise BootstrapError("Set SUPABASE_SERVICE_ROLE_KEY in your shell; never place it in browser variables")
    password = os.getenv("SILICON_DEMO_PASSWORD", "")
    if args.user_id is None and len(password) < 16:
        raise BootstrapError("Set SILICON_DEMO_PASSWORD to a unique password of at least 16 characters")

    def request(method: str, path: str, data: object | None = None, *, upsert: bool = False):
        headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}", "Content-Type": "application/json"}
        if path.startswith("/rest/"):
            headers["Prefer"] = "return=representation" + (",resolution=merge-duplicates" if upsert else "")
        encoded = None if data is None else json.dumps(data).encode("utf-8")
        req = Request(base_url + path, data=encoded, headers=headers, method=method)
        try:
            with urlopen(req, timeout=30) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except HTTPError as error:
            # Do not print server response bodies: proxies could echo credentials.
            raise BootstrapError(f"{method} {path.split('?')[0]} failed with HTTP {error.code}. Check migrations and auth user existence; use --user-id to reuse a user.") from None
        except URLError:
            raise BootstrapError("Could not connect to Supabase. Start local Supabase or verify SUPABASE_URL.") from None

    # Authentication is provisioned before memberships, satisfying all auth FKs.
    if args.user_id:
        user = request("GET", f"/auth/v1/admin/users/{args.user_id}")
        if user.get("email", "").casefold() != args.email.casefold():
            raise BootstrapError("--user-id belongs to a different email; refusing to grant membership")
    else:
        user = request("POST", "/auth/v1/admin/users", {
            "email": args.email, "password": password, "email_confirm": True,
            "user_metadata": {"name": "Demo Fab Manager", "synthetic_demo": True},
        })
    user_id = user["id"]
    tenant_id = args.tenant_id or uuid4()

    def stable_id(label: str) -> str:
        return str(uuid5(tenant_id, label))

    def put(table: str, rows: list[dict], conflict: str = "id"):
        return request("POST", "/rest/v1/" + table + "?" + urlencode({"on_conflict": conflict}), rows, upsert=True)

    def scoped(label: str, **fields) -> dict:
        return {"id": stable_id(label), "tenant_id": str(tenant_id), **fields}

    put("tenants", [{"id": str(tenant_id), "name": args.tenant_name}])
    put("memberships", [scoped("membership:manager", user_id=user_id, role="fab_manager")], "tenant_id,user_id")
    today = date.today()
    start = (today - timedelta(days=150)).isoformat()
    end = (today + timedelta(days=240)).isoformat()
    completed_at = (today - timedelta(days=10)).isoformat() + "T12:00:00Z"
    stages = ["EVT", "DVT", "PVT", "Feasibility", "Ramp/Launch", "Ideation"]
    project_defs = [
        ("HX-240", "Helix AI Accelerator", "3nm", 72, 8_400_000, 6_150_000, "at_risk"),
        ("AU-180", "Aurora Automotive MCU", "7nm", 61, 5_600_000, 3_200_000, "on_track"),
        ("NP-360", "Neptune Network ASIC", "5nm", 86, 7_200_000, 6_800_000, "delayed"),
        ("ED-110", "EdgeSense IoT Controller", "22nm", 28, 2_200_000, 480_000, "on_track"),
        ("PW-410", "PulseWave RF Front End", "28nm", 94, 3_800_000, 3_420_000, "on_track"),
        ("OC-550", "Orion Compute Chiplet", "2nm", 8, 9_600_000, 420_000, "at_risk"),
    ]
    projects = []
    for index, (code, name, node, progress, budget, spent, status) in enumerate(project_defs):
        frozen = stages[index] in {"DVT", "PVT", "Ramp/Launch"}
        projects.append(scoped(f"project:{code}", code=code, name=name, node=node, stage=stages[index],
            progress=progress, budget=budget, spent=spent, status=status, roi=2.1 + index / 10,
            start_date=start, end_date=end, owner="Demo Fab Manager", owner_id=user_id,
            strategic_alignment=92 - index * 4, design_frozen=frozen,
            freeze_approved_by=user_id if frozen else None, freeze_approved_at=completed_at if frozen else None))
    put("projects", projects)

    tasks = []
    for index, project in enumerate(projects):
        for task_index, title in enumerate(["Architecture sign-off", "Validation campaign", "Yield readiness review"]):
            tasks.append(scoped(f"task:{index}:{task_index}", project_id=project["id"], title=title,
                stage=project["stage"], status=["done", "in_progress", "todo"][task_index],
                start_date=start, end_date=end, progress=[100, 55, 0][task_index], assigned_to=user_id))
    put("tasks", tasks)
    people = [
        ("Alex Morgan", "Lead Architect", ["RTL", "SoC Architecture"], ["3nm", "5nm"]),
        ("Sam Rivera", "Validation Engineer", ["UVM", "Formal Verification"], ["3nm", "7nm"]),
        ("Jordan Chen", "Physical Design Engineer", ["STA", "Place & Route"], ["2nm", "3nm"]),
        ("Taylor Brooks", "QA Engineer", ["Reliability", "AEC-Q100"], ["7nm", "22nm"]),
        ("Casey Patel", "DFT Engineer", ["ATPG", "Scan Design"], ["5nm", "7nm"]),
        ("Drew Kim", "Process Engineer", ["Yield Analysis", "SPC"], ["22nm", "28nm"]),
    ]
    resources = [scoped(f"resource:{index}", name=name, role=role, skills=skills, fab_nodes=nodes, weekly_capacity=40)
                 for index, (name, role, skills, nodes) in enumerate(people)]
    put("resources", resources)
    allocations = [scoped(f"allocation:{index}", project_id=projects[index]["id"], resource_id=resource["id"],
                   hours_per_week=[32, 36, 38, 24, 30, 28][index], start_date=start, end_date=end)
                   for index, resource in enumerate(resources)]
    allocations.append(scoped("allocation:overload", project_id=projects[2]["id"], resource_id=resources[1]["id"],
                             hours_per_week=18, start_date=start, end_date=end))
    put("allocations", allocations)
    put("demands", [scoped(f"demand:{index}", title=title, category=category, node=node,
        estimated_budget=budget, strategic_score=score, status=status)
        for index, (title, category, node, budget, score, status) in enumerate([
            ("Optical interconnect controller", "New Product", "5nm", 4200000, 91, "under_review"),
            ("Next-gen battery management IC", "Platform Extension", "28nm", 1800000, 86, "submitted"),
            ("Secure enclave chiplet", "New Product", "3nm", 6200000, 94, "approved"),
        ])])
    put("historical_phase_metrics", [scoped(f"metric:{index}", node=["3nm", "5nm", "7nm"][index % 3],
        phase=["EVT", "DVT"][index % 2], planned_days=30 + (index % 3) * 5,
        actual_days=35 + (index % 4) * 6, completed_at=completed_at)
        for index in range(12)])
    put("time_entries", [scoped(f"time:{index}", user_id=user_id, project_id=projects[index % 3]["id"],
        task_id=tasks[(index % 3) * 3 + 1]["id"], phase=projects[index % 3]["stage"],
        work_date=(today - timedelta(days=index)).isoformat(), hours=6 + index % 3,
        billable=True, note="Synthetic demo validation work", status="draft") for index in range(5)])
    print("Synthetic development seed complete. No credentials were printed or saved.")
    print(f"Tenant ID: {tenant_id}")
    print(f"Auth user ID: {user_id}")
    print(f"Email: {args.email}")
    print("Role: fab_manager. Sign in using the unique password you supplied in the environment.")
    print("To rerun this seed, pass the same --tenant-id and --user-id. Reruns reset sample edits.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (BootstrapError, KeyError) as error:
        print(f"Bootstrap failed: {error}", file=sys.stderr)
        sys.exit(1)
