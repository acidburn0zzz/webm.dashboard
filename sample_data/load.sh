#!/bin/sh
self=${0}
dir=$(dirname $self)
HOST=${HOST:-localhost:8080}
BIN=${dir}/../tools/upload-data.py

for f in ${@:-${dir}/*.json}; do
    echo "Loading $f ..."
    case "$f" in
      *commits*.json)
         ${BIN} --host=$HOST --commit ${f}
         ;;
      *filesets.json)
         ${BIN} --host=$HOST --fileset ${f}
         ;;
      *metrics.json)
         ${BIN} --host=$HOST --metric-metadata ${f}
         ;;
      *)
         ${BIN} --host=$HOST --data ${f}
         ;;
    esac
done
