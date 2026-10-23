#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -f .work/classes/specmd/adapters/CucumberBridge.class ]]; then printf '%s\n' 'Run bash prepare.sh and bash build.sh first.' >&2; exit 2; fi
dependency_classpath="$(cat .work/classpath.txt)"
exec java -cp ".work/classes:$dependency_classpath${SPECMD_JAVA_EXTRA_CLASSPATH:+:$SPECMD_JAVA_EXTRA_CLASSPATH}" \
  specmd.adapters.CucumberBridge "$@"
