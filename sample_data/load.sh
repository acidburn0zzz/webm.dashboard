#!/bin/sh
self=${0}
dir=$(dirname $self)
HOST=${HOST:-localhost:8080}
for f in ${@:-${dir}/*.json}; do
    echo "Loading $f ..."
    case "$f" in
      *commits*.json)
         curl -F data=@${f} http://$HOST/gerrit/import-commits
         ;;
      *filesets.json)
         curl -F data=@${f} http://$HOST/import-filesets
         ;;
      *metrics.json)
         curl -F data=@${f} http://$HOST/import-metrics
         ;;
      *)
         curl -F data=@${f} http://$HOST/import-codec-metrics
         ;;
    esac
done
