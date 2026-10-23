#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
mkdir -p .work
maven_command="${SPECMD_MAVEN_COMMAND:-mvn}"
settings=()
if [[ -n "${SPECMD_MAVEN_SETTINGS:-}" ]]; then settings=(--settings "$SPECMD_MAVEN_SETTINGS"); fi
"$maven_command" --batch-mode --no-transfer-progress "${settings[@]}" \
  -Dmaven.repo.local="${SPECMD_MAVEN_REPO:-$PWD/.work/m2}" \
  org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -DincludeScope=runtime -Dmdep.outputFile=.work/classpath.txt
