#!/usr/bin/env python3
"""Split Camel modules that have unit tests into balanced shards.

Usage: plan-test-shards.py <shard-count>
Prints the shard list as a GitHub Actions matrix: {"include":[{"shard":0,"modules":"a,b"},...]}
Modules are weighted by their number of *Test.java classes and packed greedily
(heaviest first, into the currently lightest shard). Weights are capped
because class count is only a rough proxy for runtime (camel-core has ~2500
classes but runs in a few minutes).

Modules in PINNED each get a shard of their own, in addition to <shard-count>.
With -fae, a failing or hanging module makes Maven skip every module in the
same shard that depends on it, so camel-core would otherwise take dozens of
modules down with it. Other shards resolve it from the restored local
repository instead.

Modules in SKIPPED are left out of every shard because their tests cannot pass
on the Java 8 runner; each entry gives the reason.
"""
import json
import os
import sys

WEIGHT_CAP = 400
PINNED = ["core/camel-core"]
SKIPPED = {
    # KameletEipAggregateJoorTest compiles with the jOOR compiler, which needs Java 11+.
    # The test job runs on Java 8, so the module's tests fail there on every run.
    "components/camel-kamelet": "jOOR compiler needs Java 11+",
    # The tests call the live Nominatim geocoding service. It is unreachable or rate-limited
    # from the runners and the tests fail with an NPE in Double.parseDouble on the empty reply.
    # They fail the same way locally, so it is not a runner problem.
    "components/camel-geocoder": "tests call the live Nominatim service",
}
SKIP_DIRS = {"archetypes", "docs", "target", ".git", "node_modules", "src"}


def find_modules(root):
    modules = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if not os.path.isfile(os.path.join(dirpath, "pom.xml")):
            continue
        test_dir = os.path.join(dirpath, "src", "test")
        if not os.path.isdir(test_dir):
            continue
        count = sum(
            1
            for _, _, files in os.walk(test_dir)
            for f in files
            if f.endswith("Test.java")
        )
        if count:
            modules.append((min(count, WEIGHT_CAP), os.path.relpath(dirpath, root)))
    return modules


def main():
    shards = int(sys.argv[1])
    modules = sorted(find_modules("."), key=lambda m: (-m[0], m[1]))
    bins = [{"weight": 0, "modules": []} for _ in range(shards)]
    pinned = []
    for weight, path in modules:
        if path in SKIPPED:
            continue
        if path in PINNED:
            pinned.append({"weight": weight, "modules": [path]})
            continue
        target = min(bins, key=lambda b: b["weight"])
        target["weight"] += weight
        target["modules"].append(path)
    bins.extend(pinned)
    include = [
        {"shard": i, "modules": ",".join(sorted(b["modules"]))}
        for i, b in enumerate(bins)
        if b["modules"]
    ]
    for i, b in enumerate(bins):
        print(f"shard {i}: {len(b['modules'])} modules, {b['weight']} test classes", file=sys.stderr)
    print(json.dumps({"include": include}))


main()
