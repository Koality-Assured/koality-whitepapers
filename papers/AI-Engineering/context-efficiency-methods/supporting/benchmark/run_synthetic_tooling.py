#!/usr/bin/env python3
"""Run the public synthetic context-efficiency fixtures with local tools."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
FIXTURE_PATH = HERE / "tooling-fixtures.json"
DEFAULT_OUTPUT = HERE / "metrics" / "tooling-suite-results.json"
EXPECTED_TOOL_VERSIONS = {"qmd": "2.8.3", "ast-grep": "0.45.3", "trafilatura": "2.3.0"}
TEXT_HASH_NORMALIZATION = "CRLF and CR line endings normalized to LF before hashing"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_text_bytes(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def run(command: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if check and result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def version(command: str) -> str:
    executable = shutil.which(command)
    if executable is None:
        raise RuntimeError(f"Required command is not on PATH: {command}")
    result = run([executable, "--version"], HERE)
    return result.stdout.strip() or result.stderr.strip()


def validate_tool_versions() -> dict[str, str]:
    """Fail closed unless all tools match the versions used for the recorded run."""
    found: dict[str, str] = {}
    for tool, command in (("qmd", "qmd"), ("ast-grep", "ast-grep")):
        reported = version(command)
        match = re.match(rf"^{re.escape(tool)}\s+(\d+\.\d+\.\d+)(?:\s|$)", reported)
        actual = match.group(1) if match else None
        if actual != EXPECTED_TOOL_VERSIONS[tool]:
            raise RuntimeError(
                f"Unsupported {tool} version; required {EXPECTED_TOOL_VERSIONS[tool]}, "
                f"found {reported!r}"
            )
        found[tool] = reported
    try:
        trafilatura_version = importlib.metadata.version("trafilatura")
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError("Trafilatura 2.3.0 is required; package metadata was not found") from error
    if trafilatura_version != EXPECTED_TOOL_VERSIONS["trafilatura"]:
        raise RuntimeError(
            f"Unsupported Trafilatura version; required {EXPECTED_TOOL_VERSIONS['trafilatura']}, "
            f"found {trafilatura_version!r}"
        )
    found["trafilatura"] = trafilatura_version
    return found


def write_text(path: Path, content: str) -> bytes:
    encoded = content.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    return encoded


def normalize_qmd_path(value: str) -> str | None:
    if value.startswith("qmd://"):
        return value.rsplit("/", 1)[-1]
    candidate = value.replace("\\", "/").rstrip("/").split("/")[-1]
    return candidate if candidate.endswith(".md") else None


def qmd_result_items(payload: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            items.extend(qmd_result_items(item))
    elif isinstance(payload, dict):
        if isinstance(payload.get("file"), str):
            items.append(payload)
        else:
            for value in payload.values():
                if isinstance(value, (list, dict)):
                    items.extend(qmd_result_items(value))
    return items


def extract_webfetch(fixture: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    import trafilatura

    rows: list[dict[str, Any]] = []
    fixture_hashes: list[dict[str, str]] = []
    nav = "<nav>Fictional archive | Home | Index | Contact</nav>"
    repeated = " ".join(
        f"<p>Archive note {index + 1}: this is fictional navigation and catalog boilerplate.</p>"
        for index in range(fixture["boilerplate_repetitions"])
    )
    pages: dict[str, bytes] = {}
    for article in fixture["articles"]:
        html = (
            "<!doctype html><html><head><title>Fictional archive</title></head><body>"
            f"{nav}<main><article><h1>{article['title']}</h1>"
            f"<p>Reference marker: {article['marker']}. {article['fact']}</p>"
            "<p>This record is synthetic and exists only for a local extraction check.</p>"
            f"</article></main><aside>{repeated}</aside><footer>Fictional footer index.</footer>"
            "</body></html>"
        )
        pages[f"/{article['id']}.html"] = html.encode("utf-8")

    class FixtureHandler(http.server.BaseHTTPRequestHandler):
        requests_served = 0

        def do_GET(self) -> None:
            body = self.pages.get(self.path)
            if body is None:
                self.send_error(404)
                return
            type(self).requests_served += 1
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    FixtureHandler.pages = pages
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        for article in fixture["articles"]:
            path = f"/{article['id']}.html"
            raw = pages[path]
            with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}{path}", timeout=5) as response:
                fetch_status = response.status
                downloaded_bytes = response.read()
            if fetch_status != 200 or downloaded_bytes != raw:
                raise RuntimeError(f"Local HTTP fixture fetch failed for {article['id']}")
            downloaded = downloaded_bytes.decode("utf-8")
            extracted = trafilatura.extract(
                downloaded,
            output_format="txt",
            include_comments=False,
            include_tables=False,
            include_links=False,
            include_images=False,
            favor_precision=False,
            ) or ""
            extracted_bytes = extracted.encode("utf-8")
            gold_markers = [article["marker"], *article["gold_markers"]]
            retained = [marker for marker in gold_markers if marker in extracted]
            reduction = (1 - len(extracted_bytes) / len(raw)) * 100
            rows.append(
                {
                    "fixture_id": article["id"],
                    "local_fetch_status": fetch_status,
                    "raw_html_bytes": len(raw),
                    "extracted_text_bytes": len(extracted_bytes),
                    "byte_reduction_percent": round(reduction, 4),
                    "gold_markers_retained": f"{len(retained)}/{len(gold_markers)}",
                    "all_gold_markers_retained": len(retained) == len(gold_markers),
                    "input_sha256": sha256(raw),
                    "output_sha256": sha256(extracted_bytes),
                }
            )
            fixture_hashes.append({"fixture_id": article["id"], "sha256": sha256(raw)})
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
    if FixtureHandler.requests_served != len(fixture["articles"]):
        raise RuntimeError("Local synthetic web server did not receive one fetch per page")
    return rows, fixture_hashes


def run_suite(output_path: Path) -> dict[str, Any]:
    tool_versions = validate_tool_versions()
    fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    qmd_cli = shutil.which("qmd")
    ast_grep_cli = shutil.which("ast-grep")
    if qmd_cli is None or ast_grep_cli is None:
        raise RuntimeError("Both qmd and ast-grep must be available on PATH")

    qmd_documents = fixtures["qmd"]["documents"]
    qmd_total_bytes = sum(len(content.encode("utf-8")) for content in qmd_documents.values())
    qmd_rows: list[dict[str, Any]] = []
    qmd_hashes: list[dict[str, str]] = []
    ast_hashes: list[dict[str, str]] = []
    prefix_hashes: list[dict[str, str]] = []

    with tempfile.TemporaryDirectory(prefix="context-efficiency-synthetic-") as temp_name:
        temp = Path(temp_name)

        qmd_project = temp / "qmd-project"
        qmd_fixture_dir = qmd_project / "fixtures"
        qmd_fixture_dir.mkdir(parents=True)
        for filename, content in qmd_documents.items():
            raw = write_text(qmd_fixture_dir / filename, content)
            qmd_hashes.append({"fixture_id": f"QMD-DOC-{filename}", "sha256": sha256(raw)})
        run([qmd_cli, "init"], qmd_project)
        run([qmd_cli, "collection", "add", "fixtures", "--name", "synthetic"], qmd_project)
        run([qmd_cli, "update"], qmd_project)
        qmd_status = run([qmd_cli, "status"], qmd_project).stdout
        expected_index = str((qmd_project / ".qmd" / "index.sqlite").resolve()).lower()
        if expected_index not in qmd_status.lower():
            raise RuntimeError("QMD did not use the isolated temporary project index")

        for query in fixtures["qmd"]["queries"]:
            search = run(
                [qmd_cli, "search", query["query"], "--no-rerank", "--format", "json", "-c", "synthetic", "-n", "5"],
                qmd_project,
            )
            try:
                payload = json.loads(search.stdout)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"QMD did not return JSON for {query['id']}: {search.stdout}") from error
            candidates = qmd_result_items(payload)
            if not candidates:
                raise RuntimeError(f"Could not identify QMD result paths for {query['id']}: {search.stdout}")
            top_item = candidates[0]
            top = normalize_qmd_path(top_item["file"])
            if top is None:
                raise RuntimeError(f"Could not normalize QMD result file for {query['id']}")
            target_content = qmd_documents.get(top, "")
            gold_in_source = query["gold_marker"] in target_content
            gold_in_snippet = query["gold_marker"] in str(top_item.get("snippet", ""))
            reduction = (1 - len(target_content.encode("utf-8")) / qmd_total_bytes) * 100
            qmd_rows.append(
                {
                    "fixture_id": query["id"],
                    "query": query["query"],
                    "expected_file": query["expected_file"],
                    "top_file": top,
                    "top_1_match": top == query["expected_file"],
                    "gold_marker_in_selected_source_document": gold_in_source and top == query["expected_file"],
                    "gold_marker_in_top_hit_snippet": gold_in_snippet,
                    "selected_document_bytes": len(target_content.encode("utf-8")),
                    "full_fixture_corpus_bytes": qmd_total_bytes,
                    "selected_content_reduction_percent": round(reduction, 4),
                }
            )

        ast_file = temp / fixtures["ast_grep"]["file_name"]
        ast_bytes = write_text(ast_file, fixtures["ast_grep"]["source"])
        ast_hashes.append({"fixture_id": "AST-SYN-01", "sha256": sha256(ast_bytes)})
        outline = run([ast_grep_cli, "outline", "--json=compact", str(ast_file)], temp)
        outline_payload = json.loads(outline.stdout)
        outline_text = json.dumps(outline_payload, ensure_ascii=False)
        target_function = fixtures["ast_grep"]["target_function"]
        if target_function not in outline_text:
            raise RuntimeError("ast-grep outline did not identify the target function")
        pattern = f"def {target_function}($$$): $$$"
        extracted = run(
            [ast_grep_cli, "run", "--json=compact", "--pattern", pattern, "--selector", "function_definition", "--lang", "python", str(ast_file)],
            temp,
        )
        matches = json.loads(extracted.stdout)
        target_matches = [match for match in matches if match.get("text", "").startswith(f"def {target_function}(")]
        if len(target_matches) != 1:
            raise RuntimeError(f"Expected one structured ast-grep match, got {len(target_matches)}")
        selected = target_matches[0]["text"].replace("\r\n", "\n")
        selected_bytes = selected.encode("utf-8")
        ast_markers = fixtures["ast_grep"]["gold_markers"]
        ast_retained = [marker for marker in ast_markers if marker in selected]
        ast_row = {
            "fixture_id": "AST-SYN-01",
            "target_function": target_function,
            "outline_found_target": target_function in outline_text,
            "match_count": len(target_matches),
            "source_bytes": len(ast_bytes),
            "selected_bytes": len(selected_bytes),
            "byte_reduction_percent": round((1 - len(selected_bytes) / len(ast_bytes)) * 100, 4),
            "gold_markers_retained": f"{len(ast_retained)}/{len(ast_markers)}",
            "all_gold_markers_retained": len(ast_retained) == len(ast_markers),
            "input_sha256": sha256(ast_bytes),
            "output_sha256": sha256(selected_bytes),
        }
        if not ast_row["match_count"] or not ast_row["all_gold_markers_retained"]:
            raise RuntimeError(f"ast-grep selected extraction failed its fixture oracle: {ast_row}")

        prefix = fixtures["prompt_prefix"]["static_prefix"]
        prefix_bytes = prefix.encode("utf-8")
        requests = fixtures["prompt_prefix"]["requests"]
        full_prompts: list[bytes] = []
        for index, request in enumerate(requests, start=1):
            prompt = prefix + request
            raw = prompt.encode("utf-8")
            full_prompts.append(raw)
            prefix_hashes.append({"fixture_id": f"PREFIX-SYN-{index:02d}", "sha256": sha256(raw)})
        common_bytes = 0
        for left, right in zip(*full_prompts):
            if left != right:
                break
            common_bytes += 1
        prefix_row = {
            "fixture_id": "PREFIX-SYN-PAIR-01",
            "request_count": len(full_prompts),
            "declared_static_prefix_bytes": len(prefix_bytes),
            "longest_common_prefix_bytes": common_bytes,
            "static_prefix_matches_before_first_variable_byte": common_bytes == len(prefix_bytes),
            "provider_cache_hit_measured": False,
            "input_sha256": [sha256(prompt) for prompt in full_prompts],
        }
        if not prefix_row["static_prefix_matches_before_first_variable_byte"]:
            raise RuntimeError("Prompt fixtures do not share the declared static prefix")

    web_rows, web_hashes = extract_webfetch(fixtures["webfetch"])
    if not all(row["all_gold_markers_retained"] for row in web_rows):
        raise RuntimeError(f"Trafilatura did not preserve all expected synthetic web facts: {web_rows}")
    if not all(row["top_1_match"] and row["gold_marker_in_selected_source_document"] and row["gold_marker_in_top_hit_snippet"] for row in qmd_rows):
        raise RuntimeError("QMD failed at least one exact top-result fixture check")

    now = datetime.now().astimezone()
    results: dict[str, Any] = {
        "suite": fixtures["fixture_set"],
        "run_timestamp_local": now.isoformat(timespec="seconds"),
        "access_date_local": now.date().isoformat(),
        "environment": {
            "python": platform.python_version(),
            "qmd": tool_versions["qmd"],
            "ast_grep": tool_versions["ast-grep"],
            "trafilatura": tool_versions["trafilatura"],
        },
        "fixture_source_sha256": sha256(normalized_text_bytes(FIXTURE_PATH.read_bytes())),
        "fixture_source_sha256_normalization": TEXT_HASH_NORMALIZATION,
        "commands": {
            "qmd_setup": "qmd init; qmd collection add fixtures --name synthetic; qmd update",
            "qmd_search": "qmd search <query> --no-rerank --format json -c synthetic -n 5",
            "ast_grep_outline": "ast-grep outline --json=compact <synthetic_policy.py>",
            "ast_grep_extract": "ast-grep run --json=compact --pattern 'def policy_for_request($$$): $$$' --selector function_definition --lang python <synthetic_policy.py>",
            "webfetch": "urllib.request.urlopen(local_loopback_url) followed by trafilatura.extract(..., output_format='txt', favor_precision=False); fixture server binds to 127.0.0.1 only",
            "prefix_audit": "UTF-8 longest-common-prefix comparison over two complete synthetic prompts; no provider request",
        },
        "qmd": {
            "method": "BM25 lexical search; exact expected-document top-1 and marker-in-snippet checks; top document source bytes versus all five synthetic source documents",
            "queries": qmd_rows,
            "top_1_correct": f"{sum(row['top_1_match'] for row in qmd_rows)}/{len(qmd_rows)}",
            "mean_selected_source_reduction_percent": round(sum(row["selected_content_reduction_percent"] for row in qmd_rows) / len(qmd_rows), 4),
            "fixture_sha256": qmd_hashes,
            "caveat": "Small lexical fixtures only; no vector retrieval, reranking, answer-quality evaluation, or generalization claim.",
        },
        "ast_grep": {
            "method": "Outline-first discovery, then one function_definition pattern extraction; JSON match text normalized to LF before byte counting; exact target markers checked in selected source",
            "result": ast_row,
            "fixture_sha256": ast_hashes,
            "caveat": "One synthetic Python file and one target function; marker retention is not semantic correctness or runtime behavior.",
        },
        "webfetch": {
            "method": "Stdlib HTTP fetch from a temporary 127.0.0.1-only server, then Trafilatura default main-text extraction; UTF-8 byte reduction against served synthetic HTML; exact marker and fact substring checks",
            "articles": web_rows,
            "local_fetch_requests_served": len(web_rows),
            "mean_byte_reduction_percent": round(sum(row["byte_reduction_percent"] for row in web_rows) / len(web_rows), 4),
            "gold_markers_retained": f"{sum(int(row['gold_markers_retained'].split('/')[0]) for row in web_rows)}/{sum(int(row['gold_markers_retained'].split('/')[1]) for row in web_rows)}",
            "fixture_sha256": web_hashes,
            "caveat": "Five deterministic fictional pages; extraction/marker checks do not establish factuality, prompt-injection resistance, or behavior on arbitrary websites.",
        },
        "prompt_prefix": {
            "method": "Static longest-common-prefix check on two rendered synthetic prompt strings",
            "result": prefix_row,
            "fixture_sha256": prefix_hashes,
            "caveat": "Prefix equality is only a local static property; no provider request, cache hit, eligible model, billing, or latency was measured.",
        },
        "independence_note": "Each tooling fixture is a separate synthetic task. The reductions are not additive and do not estimate end-to-end savings.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else HERE / args.output
    try:
        results = run_suite(output)
    except RuntimeError as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps({
        "output": output.name,
        "access_date_local": results["access_date_local"],
        "environment": results["environment"],
        "qmd_top_1_correct": results["qmd"]["top_1_correct"],
        "ast_markers_retained": results["ast_grep"]["result"]["gold_markers_retained"],
        "webfetch_mean_byte_reduction_percent": results["webfetch"]["mean_byte_reduction_percent"],
        "webfetch_gold_markers_retained": results["webfetch"]["gold_markers_retained"],
        "prefix_common_bytes": results["prompt_prefix"]["result"]["longest_common_prefix_bytes"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
