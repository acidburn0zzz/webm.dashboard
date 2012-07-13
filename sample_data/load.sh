#!/bin/sh
self=${0}
dir=$(dirname $self)
for f in ${dir}/*.json; do
    echo "Loading $f ..."
    case "$f" in
      *commits.json)
         curl -F data=@${f} http://localhost:8080/import-commits
         ;;
      *filesets.json)
         curl -F data=@${f} http://localhost:8080/import-filesets
         ;;
      *)
         curl -F data=@${f} http://localhost:8080/import-codec-metrics
         ;;
    esac
done
