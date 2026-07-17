#!/usr/bin/env python3
"""
Create/update brainlife.io pipeline rules directly via the Warehouse API.

The `bl` CLI has no rule subcommand (only app/bids/data/datatype/profile/
project/pub/resource) -- this replicates what the web UI's RuleModal.vue
does when you click "+Add Rule" in a project's Pipeline tab:

    POST/PUT https://brainlife.io/api/warehouse/rule
    PUT      https://brainlife.io/api/warehouse/rule/order/<project_id>   (splice into the pipeline group tree)

See agent-instructions.md > "CLI use and Brainlife documentation" for the
API base URLs and auth pattern this reuses.

Usage as a library:
    from create_pipeline_rule import create_rule, add_rule_to_pipeline

    rule = create_rule(
        project="6a5939af13254aef69aecae4",
        app_id="64075386c538c16a826b5818",
        name="egi2mne (auto)",
        config={"rm_flat": True},
        input_tags={"egi1": ["raw"]},
    )
    add_rule_to_pipeline(rule["project"], rule["_id"])

Usage from the command line (one rule at a time):
    python create_pipeline_rule.py \\
        --project 6a5939af13254aef69aecae4 \\
        --app 64075386c538c16a826b5818 \\
        --name "egi2mne (auto)" \\
        --config config.json \\
        --input-tag egi1:raw \\
        --add-to-pipeline \\
        [--dry-run]
"""
import argparse
import json
import re
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

API = "https://brainlife.io/api/warehouse"
JWT_FILE = Path.home() / ".config" / "brainlife.io" / ".jwt"


def _jwt():
    return JWT_FILE.read_text().strip()


def _api(method, path, params=None, body=None):
    """Direct Warehouse API call (urllib, no 3rd-party deps -- same
    approach as replicate_pipeline.py's app_wait())."""
    url = f"{API}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(
            {k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
             for k, v in params.items() if v is not None}
        )
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {_jwt()}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def bl(*args):
    result = subprocess.run(["bl", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: bl {' '.join(args)}\n{result.stderr}")
    return result.stdout


def parse_bl_json(out):
    """Same tolerant parser as replicate_pipeline.py -- `bl ... -j` sometimes
    prints a stray debug console.log before the real JSON.stringify result."""
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        pass
    lines = out.splitlines()
    candidates = [
        i for i, line in enumerate(lines)
        if line in ("{", "[")
        and i + 1 < len(lines)
        and re.match(r'^\s*"[^"]+":', lines[i + 1])
    ]
    if not candidates:
        raise RuntimeError(f"no JSON object found in bl output:\n{out}")
    start = sum(len(l) + 1 for l in lines[:candidates[-1]])
    return json.loads(out[start:])


def fetch_app(app_id):
    res = _api("GET", "app", params={"find": {"_id": app_id}, "limit": 1})
    apps = res["apps"]
    if len(apps) != 1:
        raise RuntimeError(f"expected exactly 1 app for id={app_id}, found {len(apps)}")
    return apps[0]


def _compose_output_tag(name):
    tag = name or "untitled"
    return re.sub(r"\W", "_", tag.lower())


def build_rule_payload(app, project, name="", config=None, branch=None,
                        input_tags=None, output_tags=None,
                        subject_match="", session_match="",
                        input_subject=None, input_session=None,
                        input_multicount=None, input_selection=None, active=True):
    """Mirror RuleModal.vue's initializeAppIdsInRuleObj() +
    initializeAppConfigIdsInRuleConfigObj(): fill in every input/output id
    the app declares, defaulting config to the app's declared defaults and
    output tags to a slug of the rule name (composeOutputTag)."""
    config = dict(config or {})
    for key, spec in (app.get("config") or {}).items():
        if spec.get("type") == "input":
            continue  # file-input references, not user config -- RuleModal.vue strips these before posting
        config.setdefault(key, spec.get("default"))

    input_tags = dict(input_tags or {})
    output_tags = dict(output_tags or {})
    input_subject = dict(input_subject or {})
    input_session = dict(input_session or {})
    input_multicount = dict(input_multicount or {})
    input_selection = dict(input_selection or {})

    for inp in app.get("inputs", []):
        iid = inp["id"]
        input_tags.setdefault(iid, [])
        if inp.get("multi"):
            input_multicount.setdefault(iid, "1")

    for out in app.get("outputs", []):
        oid = out["id"]
        output_tags.setdefault(oid, [_compose_output_tag(name)])

    return {
        "project": project,
        "app": app["_id"],
        "branch": branch or app.get("github_branch"),
        "name": name,
        "active": active,
        "config": config,
        "subject_match": subject_match,
        "session_match": session_match,
        "extra_datatype_tags": {},
        "input_selection": input_selection,
        "input_tags": input_tags,
        "input_subject": input_subject,
        "input_session": input_session,
        "input_multicount": input_multicount,
        "input_project_override": {},
        "output_tags": output_tags,
        "archive": {out["id"]: {"do": out.get("archive", False), "desc": ""}
                    for out in app.get("outputs", [])},
    }


def create_rule(project, app_id, name="", config=None, branch=None,
                 input_tags=None, output_tags=None,
                 subject_match="", session_match="",
                 input_subject=None, input_session=None,
                 input_multicount=None, input_selection=None, active=True, dry_run=False):
    app = fetch_app(app_id)
    payload = build_rule_payload(
        app, project, name=name, config=config, branch=branch,
        input_tags=input_tags, output_tags=output_tags,
        subject_match=subject_match, session_match=session_match,
        input_subject=input_subject, input_session=input_session,
        input_multicount=input_multicount, input_selection=input_selection, active=active,
    )
    if dry_run:
        print(f"[dry-run] POST rule\n{json.dumps(payload, indent=2)}")
        return payload
    return _api("POST", "rule", body=payload)


def update_rule(rule_id, dry_run=False, **fields):
    if dry_run:
        print(f"[dry-run] PUT rule/{rule_id}\n{json.dumps(fields, indent=2)}")
        return fields
    return _api("PUT", f"rule/{rule_id}", body=fields)


def list_rules(project):
    res = _api("GET", "rule", params={
        "find": {"project": project}, "sort": "create_date", "limit": 500,
    })
    return res["rules"]


def get_project_pipelines(project):
    projects = parse_bl_json(bl("project", "query", "--id", project, "-j"))
    if not projects:
        raise RuntimeError(f"project not found: {project}")
    return projects[0].get("pipelines")


def _find_group(node, group_name):
    if node.get("type") != "group":
        return None
    if group_name is None or node.get("name") == group_name:
        return node
    for item in node.get("items", []):
        found = _find_group(item, group_name)
        if found:
            return found
    return None


def _contains_rule(node, rule_id):
    if node.get("type") == "rule" and node.get("ruleId") == rule_id:
        return True
    return any(_contains_rule(item, rule_id) for item in node.get("items", []))


def add_rule_to_pipeline(project, rule_id, group_name=None, dry_run=False):
    """Splice a rule into the project's Pipeline-tab group tree. If the
    project has no pipeline tree yet, initialize it from all of the
    project's existing (non-removed) rules first, same as pipelines.vue's
    load() does on first visit -- this will already include `rule_id` if
    it was just created, so no separate append is needed in that case."""
    pipelines = get_project_pipelines(project)
    if not pipelines:
        rules = list_rules(project)
        pipelines = {
            "type": "group", "name": "", "open": True, "color": "inherit",
            "items": [{"type": "rule", "ruleId": r["_id"]}
                      for r in rules if not r.get("removed")],
        }
    elif not _contains_rule(pipelines, rule_id):
        target = _find_group(pipelines, group_name) if group_name else pipelines
        if target is None:
            raise RuntimeError(f"no pipeline group named {group_name!r} in project {project}")
        target.setdefault("items", []).append({"type": "rule", "ruleId": rule_id})

    if dry_run:
        print(f"[dry-run] PUT rule/order/{project}\n{json.dumps(pipelines, indent=2)}")
        return pipelines
    return _api("PUT", f"rule/order/{project}", body=pipelines)


def set_pipeline(project, pipelines, dry_run=False):
    """Replace the project's whole pipeline tree outright (e.g. to organize
    rules into named groups) rather than incrementally splicing one rule in."""
    if dry_run:
        print(f"[dry-run] PUT rule/order/{project}\n{json.dumps(pipelines, indent=2)}")
        return pipelines
    return _api("PUT", f"rule/order/{project}", body=pipelines)


def _parse_kv_list(pairs):
    out = {}
    for pair in pairs or []:
        key, _, val = pair.partition(":")
        out.setdefault(key, []).append(val)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True, help="brainlife.io project id")
    parser.add_argument("--app", required=True, help="brainlife.io app id")
    parser.add_argument("--name", default="", help="rule name (also used as the output tag slug)")
    parser.add_argument("--branch", default=None, help="app branch (defaults to the app's registered github_branch)")
    parser.add_argument("--config", type=Path, help="path to a JSON file with app config overrides")
    parser.add_argument("--input-tag", action="append", metavar="INPUT_ID:TAG",
                         help="restrict an input to datasets carrying TAG; repeatable, e.g. --input-tag raw:clean")
    parser.add_argument("--subject-match", default="", help="regex to restrict which subjects trigger this rule")
    parser.add_argument("--session-match", default="", help="regex to restrict which sessions trigger this rule")
    parser.add_argument("--inactive", action="store_true", help="create the rule deactivated (default: active)")
    parser.add_argument("--add-to-pipeline", action="store_true", help="also splice the new rule into the project's Pipeline-tab group tree")
    parser.add_argument("--group", default=None, help="name of the pipeline group to add to (with --add-to-pipeline); default: root")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = json.loads(args.config.read_text()) if args.config else {}

    rule = create_rule(
        project=args.project, app_id=args.app, name=args.name, config=config,
        branch=args.branch, input_tags=_parse_kv_list(args.input_tag),
        subject_match=args.subject_match, session_match=args.session_match,
        active=not args.inactive, dry_run=args.dry_run,
    )
    print(json.dumps(rule, indent=2))

    if args.add_to_pipeline:
        rule_id = rule.get("_id", "DRYRUN")
        add_rule_to_pipeline(args.project, rule_id, group_name=args.group, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
