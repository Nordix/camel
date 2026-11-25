#!/usr/bin/env python3
"""Split Camel modules that have unit tests into balanced shards.

Usage: plan-test-shards.py <shard-count>
Prints the shard list as a GitHub Actions matrix: {"include":[{"shard":0,"modules":"a,b"},...]}
Modules are weighted by their number of *Test.java, *Test.groovy, *IT.java and *ITCase.java classes and packed greedily
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
    # The Groovy tests use String.stripLeading() and RouteTemplateTest rejects Java 8
    # ("Java 8 is not supported. Use Java 11 or higher"), so they fail on the Java 8 test job.
    "dsl/camel-yaml-dsl/camel-yaml-dsl": "Groovy tests need Java 11+",
    "dsl/camel-yaml-dsl/camel-yaml-dsl-common": "Groovy tests need Java 11+",
    "dsl/camel-yaml-dsl/camel-yaml-dsl-deserializers": "Groovy tests need Java 11+",
    # The tests call the live Nominatim geocoding service. It is unreachable or rate-limited
    # from the runners and the tests fail with an NPE in Double.parseDouble on the empty reply.
    # They fail the same way locally, so it is not a runner problem.
    "components/camel-geocoder": "tests call the live Nominatim service",
    # camel-catalog rebuilds its json from the target/classes of every component, so in a
    # shard that built only a few of them it fails 51 tests. build-test.yml runs these four
    # modules in the Java 8 build job instead, where the whole reactor is built.
    "catalog/camel-catalog": "run in the build job",
    "catalog/camel-catalog-lucene": "run in the build job",
    "catalog/camel-catalog-maven": "run in the build job",
    "catalog/camel-route-parser": "run in the build job",
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
            if f.endswith(("Test.java", "Test.groovy", "IT.java", "ITCase.java"))
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
