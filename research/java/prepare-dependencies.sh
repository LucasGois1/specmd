#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
mkdir -p .work
task_cache="${SPECMD_JAVA_CACHE:-/tmp/specmd-java-tools}"
mkdir -p "$task_cache"
maven_version=3.9.9
if command -v mvn >/dev/null 2>&1; then
  maven_command="$(command -v mvn)"
else
  maven_archive="$task_cache/apache-maven-$maven_version-bin.tar.gz"
  maven_base="https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/$maven_version/apache-maven-$maven_version-bin.tar.gz"
  if [[ ! -f "$maven_archive" ]]; then
    curl --fail --silent --show-error --location --connect-timeout 10 --max-time 90 --output "$maven_archive" "$maven_base"
  fi
  curl --fail --silent --show-error --location --connect-timeout 10 --max-time 30 --output "$maven_archive.sha512" "$maven_base.sha512"
  python3 - "$maven_archive" <<'PY'
import hashlib, pathlib, sys
p=pathlib.Path(sys.argv[1])
expected=pathlib.Path(str(p)+'.sha512').read_text().split()[0].lower()
actual=hashlib.sha512(p.read_bytes()).hexdigest()
if actual != expected:
    raise SystemExit('Maven archive SHA-512 mismatch')
print('Maven archive checksum verified')
PY
  if [[ ! -d "$task_cache/apache-maven-$maven_version" ]]; then
    tar -xzf "$maven_archive" -C "$task_cache"
  fi
  maven_command="$task_cache/apache-maven-$maven_version/bin/mvn"
fi

# Maven does not automatically use curl's HTTP(S)_PROXY environment variables.
# Only the proxy host/port are written, never credential values.
python3 - <<'PY'
import os, pathlib, urllib.parse, xml.sax.saxutils
proxy=urllib.parse.urlparse(os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY') or '')
body=''
if proxy.hostname:
    host=xml.sax.saxutils.escape(proxy.hostname)
    port=proxy.port or (443 if proxy.scheme == 'https' else 80)
    body=f'<proxies><proxy><id>session-proxy</id><active>true</active><protocol>http</protocol><host>{host}</host><port>{port}</port></proxy></proxies>'
pathlib.Path('.work/settings.xml').write_text('<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0">'+body+'</settings>')
PY
timeout 180 "$maven_command" --batch-mode --no-transfer-progress --settings .work/settings.xml \
  -Dmaven.repo.local="$task_cache/m2" \
  -Dmaven.wagon.http.connectionTimeout=10000 -Dmaven.wagon.http.readTimeout=30000 \
  org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -DincludeScope=runtime -Dmdep.outputFile=.work/classpath.txt

python3 - <<'PY'
import hashlib, json, pathlib
entries=[]
for item in pathlib.Path('.work/classpath.txt').read_text().strip().split(':'):
    p=pathlib.Path(item)
    entries.append({'artifact':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
pathlib.Path('evidence/dependency-checksums.json').write_text(json.dumps(entries,indent=2)+'\n')
print(f'Ready: {len(entries)} dependency jars')
PY
