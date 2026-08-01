#!/usr/bin/env python3
"""
THE SPEND GATE — PreToolUse, one script, registered in both hosts.

Reads the hook payload as JSON on stdin. Refuses any Higgsfield call that spends
credits unless a preflight receipt exists for THE EXACT PROMPT about to be fired.

    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": "..."}}

Claude Code and Codex share this wire format, these matchers and these exit
codes, so one file serves both. What differs is only WHERE the registration
lives, and the registration is generated (see `hooks/registration/README.md`)
rather than shipped with a guessed variable in it.

DENY BY DEFAULT, AND WHY
------------------------
The first version of this gate matched a list of spending tools:
`generate|upscale|outpaint|reframe|motion_control|remove_background`. It missed
`generate_3d`, `dubbing`, `voice_change`, `create_voice`, `explainer_video`,
`shorts_studio_create`, `personal_clipper_create`, `video_analysis_create` and
`apps_invoke` -- several of which spend -- and would miss anything shipped next
month.

F-56 already said it: *a guard whose reach is an allow-list only ever guards what
has already gone wrong once.* Writing one into the gate whose entire job is
stopping spend was that lesson ignored in the place it mattered most.

So: the matcher takes the WHOLE server, and this script allows the calls it can
name as free. A tool nobody has classified is DENIED, with the reason and the
one-line fix. A new spending tool is gated the day it appears; a new free tool
costs one line whose worst failure is a needless prompt.

THIS IS HALF THE ENFORCEMENT
----------------------------
Both hosts require the operator to TRUST a repo-committed hook before it runs.
Until that happens this file is inert, and an inert gate is indistinguishable
from a permissive one. The other half lives in the tools: preflight will not
write a receipt without a green run including the manual items. Never rely on
this file alone -- `filmkit-doctor` reports registered and trusted as two
separate states for exactly this reason.
"""
import json, pathlib, sys

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "tools"))

# ---------------------------------------------------------------------------
# FREE — read-only, or the setup around a generation. Allowed without a receipt.
# Uploading a reference costs nothing and blocking it is friction with no safety
# behind it. Everything here is NAMED, never pattern-matched, so adding one is a
# deliberate act rather than a widened wildcard.
# ---------------------------------------------------------------------------
FREE = {
    # the account
    "balance", "transactions", "show_plans_and_credits", "list_workspaces",
    "select_workspace", "cancel_trial_auto_renewal",
    # looking at what already exists
    "show_generations", "show_medias", "show_characters", "show_reference_elements",
    "show_marketing_studio", "show_marketing_studio_generations", "job_display",
    "list_voices", "list_websites", "list_website_categories", "presets_show",
    "models_explore", "apps_search", "apps_describe", "animation_actions",
    "get_explainer_presets", "resolve_explainer_preset",
    "personal_clipper_jobs", "personal_clipper_status",
    "shorts_studio_list_presets", "shorts_studio_list_sessions", "shorts_studio_status",
    "video_analysis_jobs", "video_analysis_status", "tiktok_publish_status",
    "tiktok_accounts", "tiktok_music_trending",
    "website_status", "website_db", "website_repo_access", "website_secrets",
    # instructions and bundles — text, no spend
    "get_game_creation_instructions", "get_game_creation_bundle_file",
    "get_website_creation_instructions", "get_website_creation_bundle_file",
    "get_workflow_instructions", "get_workflow_bundle_file",
    # getting material IN
    "media_upload", "media_upload_widget", "media_import_url", "media_confirm",
}


def find_film(start):
    """
    Locate the film from the directory the HOST reports, walking up.

    The gate used to reach `_project`, which resolves from the PROCESS's cwd. A
    hook's cwd is whatever the host chose, and if it is not the film directory
    `_project` raises SystemExit -- the gate exits non-zero, both hosts read that
    as a hook FAILURE, and a hook failure lets the call through. The gate would
    have stopped gating and said nothing.

    The payload carries `cwd`. Use it.
    """
    d = pathlib.Path(start or ".").resolve()
    for cand in [d] + list(d.parents):
        f = cand / "film_facts.json"
        if f.exists():
            return cand, f
        found = sorted(cand.glob("*_facts.json"))
        if len(found) == 1:
            return cand, found[0]
    return None, None


def decide(payload, *, now_utc=None, film_dir=None):
    """Pure function: payload in, (decision, reason) out. Testable without a host."""
    tool_full = payload.get("tool_name") or ""
    if not tool_full.startswith("mcp__higgsfield__"):
        return "allow", ""
    tool = tool_full[len("mcp__higgsfield__"):]

    if tool in FREE:
        return "allow", ""

    args = payload.get("tool_input") or {}
    params = args.get("params") if isinstance(args.get("params"), dict) else {}
    # ORDER MATTERS. `params.prompt` is where this server actually carries the
    # prompt; `description` is a generic field that may be something else
    # entirely. Checking description first would hash the wrong string, and a
    # hash of the wrong string is not a check of the right one.
    prompt = ""
    for src in (args.get("prompt"), params.get("prompt"),
                args.get("text"), args.get("input_text"), args.get("description")):
        if isinstance(src, str) and src.strip():
            prompt = src
            break

    if not prompt:
        return "deny", (
            f"filmkit REFUSED {tool}. It is not classified as free and there is no prompt in "
            f"the call to check against a receipt. If this tool cannot spend credits, add it "
            f"to FREE in hooks/gate.py — deliberately, with the reason.")

    import datetime as _dt
    import json as _json
    import _project as P
    import _receipt as R

    if film_dir:
        film, facts_path = pathlib.Path(film_dir), None
        facts = {}
        for c in sorted(pathlib.Path(film_dir).glob("*_facts.json")):
            facts_path = c
            break
    else:
        film, facts_path = find_film(payload.get("cwd"))
        facts = {}
    if film is None:
        return "deny", (
            f"filmkit REFUSED {tool}. No film found from {payload.get('cwd')!r} — expected a "
            f"film_facts.json at or above it. The gate will not authorise a spend it cannot "
            f"check. If this is deliberate, run outside a film without the hook registered.")
    if facts_path is not None and facts_path.exists():
        try:
            facts = _json.loads(facts_path.read_text(encoding="utf-8"))
        except Exception as e:
            return "deny", (f"filmkit REFUSED {tool}. The film's facts file could not be read "
                            f"({e}). Refusing rather than assuming.")

    now = now_utc or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec = R.read(film, prompt)
    bad = R.check(rec, fact_rev=facts.get("_fact_rev"),
                  kit_version=P.kit_version(), now_utc=now)
    if not bad:
        return "allow", ""

    lines = [f"filmkit REFUSED {tool}. " + "; ".join(bad) + "."]
    if rec is None:
        lines.append(
            f"This prompt hashes to {R.short(R.digest(prompt))}. A receipt is written only by "
            f"an ALL-GREEN preflight — every automatic phase, plus the manual items a person "
            f"signs. Run: python3 $FILMKIT/tools/preflight.py --block \"<BLOCK>\" "
            f"--record RUN.md --export OUT.txt")
        lines.append(
            "If you edited the prompt after preflight, that is the gate working: the hash "
            "moved, so the run that was reviewed is not the run about to fire.")
    return "deny", " ".join(lines)


def _deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    return 0


def main():
    """
    EVERY exit from here is 0 with a decision, or 0 with a DENY. Never a raise.

    This is the whole safety property and the first version did not have it. Only
    JSON parse errors were caught; anything else propagated. Run outside a film
    directory, `_project` raised SystemExit, the gate exited 1 with no
    hookSpecificOutput -- and both hosts read a non-zero exit that is not 2 as a
    hook FAILURE, which means the call proceeds.

    So the gate stopped gating, silently, in exactly the situation where somebody
    is most likely to be experimenting: outside a project. That is FK-03's lesson
    -- a hook that fails, fails OPEN -- rebuilt inside the gate one commit after
    writing it down.

    A gate is a thing that says no when it cannot say yes.
    """
    if "--selftest" in sys.argv:
        return selftest()
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        return _deny(f"filmkit gate could not read the hook payload ({e}). "
                     f"Refusing rather than assuming.")
    try:
        decision, reason = decide(payload)
    except BaseException as e:                     # SystemExit included, deliberately
        return _deny(f"filmkit gate raised {type(e).__name__}: {e}. A gate that cannot "
                     f"answer the question must not answer 'yes' to it. Fix the gate, or "
                     f"unregister the hook if you mean to work without it.")
    if decision == "allow":
        return 0
    return _deny(reason)


# ---------------------------------------------------------------------------
# SELFTEST. A gate cannot be tested by running a host, so it is tested by
# feeding it payloads. Every case below is a decision the gate must get right,
# and four of them are decisions the FIRST version got wrong.
# ---------------------------------------------------------------------------
def selftest():
    import tempfile
    import _project as P
    import _receipt as R

    NOW = "2026-08-01T12:00:00Z"
    ok = True

    def case(name, payload, want, **kw):
        nonlocal ok
        got, reason = decide(payload, now_utc=NOW, **kw)
        if got != want:
            ok = False
        print(f"  {'ok ' if got == want else '!! '}{name:54s} want {want:5s} got {got}")
        if got != want and reason:
            print(f"      {reason[:150]}")

    def call(tool, **args):
        return {"tool_name": f"mcp__higgsfield__{tool}", "tool_input": args}

    print("\n  GATE SELFTEST\n")
    case("another server is none of our business",
         {"tool_name": "mcp__Gmail__search_threads", "tool_input": {}}, "allow")
    case("reading the balance is free", call("balance"), "allow")
    case("uploading a reference is free", call("media_upload", path="x.png"), "allow")
    case("generate_video with no receipt", call("generate_video", prompt="a man"), "deny")
    case("generate_3d — missed by the first matcher",
         call("generate_3d", prompt="a whale"), "deny")
    case("dubbing — missed by the first matcher", call("dubbing", prompt="x"), "deny")
    case("apps_invoke — missed by the first matcher", call("apps_invoke", prompt="x"), "deny")
    case("an unclassified tool is denied, not guessed",
         call("some_new_paid_thing", prompt="x"), "deny")
    case("a spending tool with no prompt to check", call("upscale_video", id="abc"), "deny")

    with tempfile.TemporaryDirectory() as d:
        # A REAL film, however small. The first version wrote receipts using the
        # surrounding film's fact_rev while the gate read the empty temp dir's --
        # 103 against None -- so two cases failed for a reason that had nothing to
        # do with the gate. It also meant `--selftest` only worked from inside a
        # film, which is the wrong dependency for a test of a hook.
        FACT_REV = 7
        (pathlib.Path(d) / "film_facts.json").write_text(
            json.dumps({"_fact_rev": FACT_REV, "kit_version": P.kit_version(),
                        "look_pack": None, "assets": {}}), encoding="utf-8")
        text = "SCENE CONTEXT\nA man at a window.\n"
        good = dict(block="X", fact_rev=FACT_REV,
                    kit_version=P.kit_version(),
                    phases={"guards": True, "manual": True}, stamp=NOW)
        R.write(d, text, **good)
        case("the exact prompt, fresh receipt",
             call("generate_video", prompt=text), "allow", film_dir=d)
        case("trailing whitespace and CRLF still match",
             call("generate_video", prompt=text.replace("\n", "  \r\n") + "\n\n"),
             "allow", film_dir=d)
        case("one word edited after preflight",
             call("generate_video", prompt=text.replace("man", "woman")), "deny", film_dir=d)

        R.write(d, text, **{**good, "phases": {"guards": True, "manual": False}})
        case("a run whose manual items failed",
             call("generate_video", prompt=text), "deny", film_dir=d)

        R.write(d, text, **{**good, "fact_rev": -999})
        case("the facts moved under the receipt",
             call("generate_video", prompt=text), "deny", film_dir=d)

        R.write(d, text, **{**good, "stamp": "2026-07-01T12:00:00Z"})
        case("a receipt older than the limit",
             call("generate_video", prompt=text), "deny", film_dir=d)

    # ---- END-TO-END. The cases above call decide(); the fail-OPEN bug lived in
    # main(), where an uncaught exception exited non-zero with no decision. A
    # decide()-level test could never have caught it. These run the script.
    import subprocess as _sp
    print("\n  FAIL-CLOSED (the script, not the function)\n")

    def e2e(name, payload_text, cwd="/"):
        nonlocal ok
        r = _sp.run([sys.executable, str(pathlib.Path(__file__).resolve())],
                    input=payload_text, capture_output=True, text=True, cwd=cwd)
        denied = '"permissionDecision": "deny"' in r.stdout
        good = denied and r.returncode == 0
        if not good:
            ok = False
        print(f"  {'ok ' if good else '!! '}{name:54s} exit {r.returncode}  "
              f"{'deny' if denied else 'NO DECISION'}")

    e2e("outside any film",
        json.dumps({"tool_name": "mcp__higgsfield__generate_video",
                    "cwd": "/", "tool_input": {"prompt": "x"}}))
    e2e("unparseable stdin", "this is not json")
    e2e("tool_input is not a dict",
        json.dumps({"tool_name": "mcp__higgsfield__generate_video",
                    "cwd": "/", "tool_input": "a string"}))
    e2e("payload is a list, not an object", json.dumps([1, 2, 3]))

    print()
    if ok:
        print("  \033[92mEvery case decided correctly.\033[0m")
        print("  NOT tested here: whether the host actually invokes this file, or whether the")
        print("  operator has TRUSTED it. Both are filmkit-doctor's job, and an untrusted gate")
        print("  is inert — which is why preflight also refuses to write the receipt.\n")
        return 0
    print("  \033[91mFAILED — do not rely on this gate.\033[0m\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
