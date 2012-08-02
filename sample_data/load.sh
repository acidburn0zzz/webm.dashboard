#!/bin/sh
self=${0}
dir=$(dirname $self)
for f in ${1:-${dir}/*.json}; do
    echo "Loading $f ..."
    case "$f" in
      *commits.json)
         curl -F data=@${f} http://localhost:8080/gerrit/import-commits
         ;;
      *filesets.json)
         curl -F data=@${f} http://localhost:8080/import-filesets
         ;;
      *metrics.json)
         curl -F data=@${f} http://localhost:8080/import-metrics
         ;;
      *)
         curl -F data=@${f} http://localhost:8080/import-codec-metrics
         ;;
    esac
done
