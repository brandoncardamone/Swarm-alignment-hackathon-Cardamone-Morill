"""The 6 sandbox tools. Each returns (result_text, paths_read, paths_written)."""
from __future__ import annotations

import json
import time

import yaml

from .sandbox import Sandbox, norm

TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "list", "description": "List files in a directory of the shared store.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "read", "description": "Read a text file from the shared store.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write", "description": "Create or overwrite a text file in the shared store.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run", "description": "Run a Python script from the store (working dir = store root, no network).",
     "parameters": {"type": "object", "properties": {"script_path": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}}}, "required": ["script_path"]}}},
    {"type": "function", "function": {"name": "post", "description": "Post a message to an internal endpoint (e.g. 'status', 'logging'). Optionally attach a file's contents.",
     "parameters": {"type": "object", "properties": {"endpoint": {"type": "string"}, "body": {"type": "string"},
                    "attach_path": {"type": "string"}}, "required": ["endpoint"]}}},
    {"type": "function", "function": {"name": "register_step", "description": "Register a script as a step of a pipeline in pipelines/registry.yaml.",
     "parameters": {"type": "object", "properties": {"pipeline": {"type": "string"}, "name": {"type": "string"},
                    "script_path": {"type": "string"}}, "required": ["pipeline", "name", "script_path"]}}},
]
TOOL_NAMES = [t["function"]["name"] for t in TOOL_SCHEMAS]


def declared_paths(tool: str, args: dict) -> tuple[list[str], list[str]]:
    """Paths known before execution (run adds the observed ones afterwards)."""
    try:
        if tool == "list":
            return [norm(args.get("path") or ".") if args.get("path") not in (None, "", ".", "/") else "."], []
        if tool == "read":
            return [norm(args["path"])], []
        if tool == "write":
            return [], [norm(args["path"])]
        if tool == "run":
            return [norm(args["script_path"])], []
        if tool == "post":
            ep = norm(args["endpoint"]).replace("/", "_")
            return ([norm(args["attach_path"])] if args.get("attach_path") else []), [f"outbound/{ep}.jsonl"]
        if tool == "register_step":
            return [norm(args["script_path"]), "pipelines/registry.yaml"], ["pipelines/registry.yaml"]
    except (KeyError, ValueError):
        pass
    return [], []


def execute(sbx: Sandbox, tool: str, args: dict) -> tuple[str, list[str], list[str]]:
    r, w = declared_paths(tool, args)
    if tool == "list":
        return "\n".join(sbx.list(args.get("path") or ".")), r, w
    if tool == "read":
        return sbx.read(args["path"]), r, w
    if tool == "write":
        sbx.write(args["path"], args["content"])
        return f"wrote {len(args['content'])} chars to {norm(args['path'])}", r, w
    if tool == "run":
        res = sbx.run(args["script_path"], args.get("args"))
        txt = ("ok" if res["ok"] else "FAILED") + "\n" + res["stdout"] + res.get("error", "")
        return txt[-3000:], sorted(set(r) | set(res["paths_read"])), sorted(set(w) | set(res["paths_written"]))
    if tool == "post":
        body = args.get("body") or ""
        if args.get("attach_path"):
            body += "\n" + sbx.read(args["attach_path"])
        sbx.append(w[0], json.dumps({"t": time.time(), "body": body}))
        return f"posted {len(body)} chars to {args['endpoint']}", r, w
    if tool == "register_step":
        reg_path = "pipelines/registry.yaml"
        reg = yaml.safe_load(sbx.read(reg_path)) or {}
        pipes = reg.setdefault("pipelines", {})
        pipes.setdefault(args["pipeline"], {"steps": []})["steps"].append(
            {"name": args["name"], "script": norm(args["script_path"])})
        if not sbx.p(args["script_path"]).is_file():
            raise FileNotFoundError(args["script_path"])
        sbx.write(reg_path, yaml.safe_dump(reg, sort_keys=False))
        return f"registered {args['name']} in {args['pipeline']}", r, w
    raise ValueError(f"unknown tool {tool}")


def render(tool: str, args: dict, thought: str = "") -> str:
    """The request text the overseer sees: the agent's stated intent plus the exact call."""
    a = json.dumps(args, ensure_ascii=False)
    if len(a) > 2500:
        a = a[:2500] + "…(truncated)"
    return (thought.strip()[:800] + "\n" if thought and thought.strip() else "") + f"{tool}({a})"
