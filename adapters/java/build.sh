#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -f .work/classpath.txt ]]; then printf '%s\n' 'Run bash prepare.sh first.' >&2; exit 2; fi
mkdir -p .work/classes
dependency_classpath="$(cat .work/classpath.txt)"
java -m jdk.compiler/com.sun.tools.javac.Main -encoding UTF-8 \
  -cp "$dependency_classpath" -d .work/classes \
  src/main/java/specmd/adapters/CucumberBridge.java \
  src/main/java/specmd/example/Application.java src/main/java/specmd/example/Steps.java
