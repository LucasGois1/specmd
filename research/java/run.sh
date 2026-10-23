#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -f .work/classpath.txt ]]; then
  printf '%s\n' 'Run ./prepare-dependencies.sh first (network required).' >&2
  exit 2
fi
mkdir -p .work/classes evidence
dependency_classpath="$(cat .work/classpath.txt)"
java -m jdk.compiler/com.sun.tools.javac.Main -encoding UTF-8 \
  -cp "$dependency_classpath" -d .work/classes \
  src/main/java/specmd/research/Application.java \
  src/main/java/specmd/research/Steps.java \
  src/main/java/specmd/research/CliCounter.java \
  src/main/java/specmd/research/Probe.java
java -cp ".work/classes:$dependency_classpath" specmd.research.Probe . evidence/results.json \
  | tee evidence/run.log
