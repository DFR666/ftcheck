"""Report modules of installed distributions that re-enable the GIL on free-threaded CPython."""
import argparse
import json
import os
import subprocess
import sys

PROBE = r'''
import sys, json, re, warnings, importlib
import importlib.metadata as md
dist, deep = sys.argv[1], sys.argv[2] == "1"
SKIP = re.compile(r"(^|\.)(tests?|testing|conftest|__main__|setup|examples?|benchmarks?|docs?)(\.|$)")
mods = set()
for f in md.files(dist) or []:
    p = list(f.parts)
    if not p or p[0] == ".." or p[0].endswith((".dist-info", ".data", ".libs")):
        continue
    name = p[-1]
    if name.endswith(".py"):
        stem = name[:-3]
    elif name.endswith((".so", ".pyd")):
        stem = name.split(".")[0]
    else:
        continue
    parts = p[:-1] + ([] if stem == "__init__" else [stem])
    if not deep:
        parts = parts[:1]
    if parts and all(x.isidentifier() for x in parts):
        m = ".".join(parts)
        if not SKIP.search(m):
            mods.add(m)
errors = {}
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    for m in sorted(mods, key=lambda s: (s.count("."), s)):
        try:
            importlib.import_module(m)
        except BaseException as e:
            errors[m] = type(e).__name__
    msgs = [str(x.message) for x in w if "GIL" in str(x.message)]
culprits = [re.search(r"load module '([^']+)'", s).group(1) for s in msgs if "load module" in s]
print("RESULT " + json.dumps({"dist": dist, "modules": len(mods), "import_errors": errors,
                              "gil_enabled": sys._is_gil_enabled(), "culprits": culprits}))
'''


def check(dist, deep, timeout):
    env = {k: v for k, v in os.environ.items() if k != "PYTHON_GIL"}
    try:
        out = subprocess.run([sys.executable, "-c", PROBE, dist, "1" if deep else "0"],
                             capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"dist": dist, "error": "timeout"}
    line = [l for l in out.stdout.splitlines() if l.startswith("RESULT ")]
    if not line:
        return {"dist": dist, "error": (out.stderr or "no output")[-300:]}
    return json.loads(line[-1][7:])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dists", nargs="+", help="installed distribution names, e.g. numpy lxml")
    ap.add_argument("--top-level", action="store_true", help="import only top-level modules")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--json", action="store_true", help="print machine-readable results")
    a = ap.parse_args()
    if not hasattr(sys, "_is_gil_enabled"):
        sys.exit("ftcheck needs CPython 3.13 or later")
    if sys._is_gil_enabled():
        sys.exit("the GIL is already enabled: use a free-threaded interpreter (e.g. python3.14t) and unset PYTHON_GIL")
    results = [check(d, not a.top_level, a.timeout) for d in a.dists]
    if a.json:
        print(json.dumps(results, indent=2))
    failed = False
    for r in results:
        if "error" in r:
            failed = True
            print(f"ERROR  {r['dist']}: {r['error']}")
        elif r["gil_enabled"]:
            failed = True
            print(f"GIL    {r['dist']}: re-enabled by {', '.join(r['culprits']) or 'unknown module'}")
        else:
            print(f"OK     {r['dist']}: {r['modules']} modules imported, GIL stays disabled")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
