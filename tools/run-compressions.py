#!/usr/bin/python

import fnmatch
import getopt
import json
import os
import subprocess
from string import Template
import sys
import urllib
import urllib2

METRIC_POST_URL = "http://%s/import-codec-metrics"
FILESET_POST_URL = "http://%s/import-filesets"
JENKINS_BUILD_URL = "http://build.webmproject.org/jenkins/job/encode-build/build"
LONG_OPTIONS = ["shard=", "shards=", "build", "src-path=", "bin-path=",
                "vid-path=", "host=", "update-filesets", "commit=",
                "remote", "token="]

def Usage(selfname):
  print "Usage: %s [options] <config ...> <fileset ...>"%selfname
  print
  print "Options:"
  print "  --shard=n        index of this shard"
  print "  --shards=n       total number of shards"
  print "  --src-path=path  path to source tree"
  print "  --bin-path=path  path to built binaries"
  print "  --vid-path=path  path to input videos"
  print "  --host=host:port dashboard server to upload to"
  print "  --commit=sha1    commit id to use"
  print "  --token=token    auth token to use with Jenkins"
  print
  print "Commands:"
  print "  --build            create executables only"
  print "  --update-filesets  update fileset definitions on server"
  print "  --remote           trigger a remote build/compress"

FILES = {
  'akiyo_cif.y4m': {'frames': 300},
  'bowing_cif.y4m': {'frames': 300},
  'bridge-close_cif.y4m': {'frames': 2000},
  'bridge-far_cif.y4m': {'frames': 2101},
  'bus_cif.y4m': {'frames': 150},
  'cheer_sif.y4m': {'frames': 299},
  'city_4cif.y4m': {'frames': 600},
  'city_4cif.y4m': {'frames': 600},
  'city_cif.y4m': {'frames': 300},
  'coastguard_cif.y4m': {'frames': 300},
  'container_cif.y4m': {'frames': 300},
  'crew_4cif.y4m': {'frames': 600},
  'crew_4cif.y4m': {'frames': 600},
  'crew_cif.y4m': {'frames': 300},
  'deadline_cif.y4m': {'frames': 1374},
  'flower_cif.y4m': {'frames': 250},
  'flower_garden_422_cif.y4m': {'frames': 360},
  'football_422_cif.y4m': {'frames': 360},
  'football_cif.y4m': {'frames': 260},
  'foreman_cif.y4m': {'frames': 300},
  'galleon_422_cif.y4m': {'frames': 360},
  'hall_monitor_cif.y4m': {'frames': 300},
  'harbour_4cif.y4m': {'frames': 600},
  'harbour_4cif.y4m': {'frames': 600},
  'harbour_cif.y4m': {'frames': 300},
  'highway_cif.y4m': {'frames': 2000},
  'husky_cif.y4m': {'frames': 250},
  'ice_4cif.y4m': {'frames': 480},
  'ice_4cif.y4m': {'frames': 480},
  'ice_cif.y4m': {'frames': 240},
  'intros_422_cif.y4m': {'frames': 360},
  'mad900_cif.y4m': {'frames': 900},
  'mobile_calendar_422_cif.y4m': {'frames': 360},
  'mobile_cif.y4m': {'frames': 300},
  'mother_daughter_cif.y4m': {'frames': 300},
  'news_cif.y4m': {'frames': 300},
  'pamphlet_cif.y4m': {'frames': 300},
  'paris_cif.y4m': {'frames': 1065},
  'sign_irene_cif.y4m': {'frames': 540},
  'silent_cif.y4m': {'frames': 300},
  'soccer_4cif.y4m': {'frames': 600},
  'soccer_4cif.y4m': {'frames': 600},
  'soccer_cif.y4m': {'frames': 300},
  'stefan_cif.y4m': {'frames': 90},
  'students_cif.y4m': {'frames': 1007},
  'tempete_cif.y4m': {'frames': 260},
  'tennis_sif.y4m': {'frames': 150},
  'vtc1nw_422_cif.y4m': {'frames': 360},
  'washdc_422_cif.y4m': {'frames': 360},
  'waterfall_cif.y4m': {'frames': 260},
}

FILE_SETS = {
  'std-cif-low': {
  'files': [
    'akiyo_cif.y4m',
    'bowing_cif.y4m',
    'pamphlet_cif.y4m',
    ],
  'bitrates': [25,50,75,100,150,200,250,300,350,400]
  },
  'std-cif-low2': {
  'files': [
    'deadline_cif.y4m',
    'ice_cif.y4m',
    'mother_daughter_cif.y4m',
    'news_cif.y4m',
    'paris_cif.y4m',
    'sign_irene_cif.y4m',
    'silent_cif.y4m',
    'students_cif.y4m',
    'container_cif.y4m',
    ],
  'bitrates': [50,100,150,200,300,400,600,800,1000]
  },
  'std-cif-med': {
  'files': [
    'city_cif.y4m',
    'foreman_cif.y4m',
    'hall_monitor_cif.y4m',
    'highway_cif.y4m',
    'waterfall_cif.y4m',
    ],
  'bitrates': [50,100,150,200,300,400,600,800,1200,1600,2000,2800]
  },
  'std-cif-high': {
  'files': [
    'bus_cif.y4m',
    'cheer_sif.y4m',
    'coastguard_cif.y4m',
    'crew_cif.y4m',
    'flower_cif.y4m',
    'football_cif.y4m',
    'harbour_cif.y4m',
    'husky_cif.y4m',
    'mobile_cif.y4m',
    'soccer_cif.y4m',
    'stefan_cif.y4m',
    'tempete_cif.y4m',
    'tennis_sif.y4m',
    ],
  'bitrates': [100,200,300,400,600,800,1200,1600,2000,2800,3600,4400,5200]
  },
}

GOOD0_VBR_FLAGS = (
  'vpxenc --good --end-usage=vbr '
  '--target-bitrate=${bitrate} -o ${outfile} ${infile}')

TWOPASS_GOOD0_VBR_FLAGS = (
  'vpxenc --passes=2 --good --end-usage=vbr '
  '--kf-max-dist=9999 --kf-min-dist=0 '
  '--lag-in-frames=25 --auto-alt-ref=1 '
  '--arnr-maxframes=7 --arnr-strength=5 --arnr-type=3 '
  '--undershoot-pct=100 '
  '--target-bitrate=${bitrate} -o ${outfile} ${infile}')

CONFIGS = {
  'twopass-good0-vbr': {
    'configure_flags': '--enable-internal-stats',
    'runtime_flags': TWOPASS_GOOD0_VBR_FLAGS
  },
  'good0-vbr': {
    'configure_flags': '--enable-internal-stats',
    'runtime_flags': GOOD0_VBR_FLAGS,
  },
  'good': {
    'configure_flags': '--enable-internal-stats',
    'runtime_flags': GOOD0_VBR_FLAGS,
  },
  'exp-twopass-good0-vbr': {
    'configure_flags': '--enable-experimental --enable-internal-stats',
    'runtime_flags': TWOPASS_GOOD0_VBR_FLAGS,
  },
  'exp-good0-vbr': {
    'configure_flags': '--enable-experimental --enable-internal-stats',
    'runtime_flags': GOOD0_VBR_FLAGS,
  },
}


def SelectRuns(globs, shard, shards):
  index = 0
  results = []
  all_configs = set()
  all_runs = {}

  for glob in globs:
    all_configs.update(fnmatch.filter(CONFIGS.keys(), glob))
    for fileset_name, fileset_data in FILE_SETS.iteritems():
      if fnmatch.fnmatch(fileset_name, glob):
        matching_files = fileset_data['files']
      else:
        matching_files = fnmatch.filter(fileset_data['files'], glob)
      for f in matching_files:
        all_runs.setdefault(f, set()).update(fileset_data['bitrates'])

  for config in sorted(all_configs):
    for f, bitrates in all_runs.iteritems():
      for b in sorted(bitrates):
        if index % shards == shard:
          result = dict(CONFIGS[config])
          result.update({'config': config, 'filename': f, 'bitrate': b})
          results.append(result)
        index += 1
  return sorted(results, key=lambda x: x['configure_flags'])


def RunCommand(command, stdout=None, env=None):
  environment = dict(os.environ)
  if env:
    environment.update(env)
  if stdout:
    pstdout = subprocess.PIPE
  else:
    pstdout = None

  print "+ " + " ".join(command)
  run = subprocess.Popen(command, stdout=pstdout, env=environment)
  output = run.communicate()
  if run.returncode:
    print "Non-zero return code: " + str(run.returncode) + " => exiting!"
    sys.exit(1)
  if stdout:
    return output[0]


def Build(runs, src_path, bin_path):
  configure_flags = None
  config = None
  for run in runs:
    if run['configure_flags'] != configure_flags:
      configure_flags = run['configure_flags']
      configure_cmd = [os.path.join(src_path, 'configure')]
      configure_cmd += configure_flags.split(" ")
      RunCommand(configure_cmd)
      RunCommand(['make', 'clean'])
      RunCommand(['make'])
    if run['config'] != config:
      config = run['config']
      srcfile = run['runtime_flags'].split(" ")[0]
      outfile = '.'.join([srcfile, run['config']])
      outfile = os.path.join(bin_path, outfile)
      RunCommand(['cp', srcfile, outfile])


def GetCommit(src_path):
  # Get commit
  git_env = {'GIT_DIR': os.path.join(src_path, ".git"),
             'GIT_WORK_TREE': src_path,
            }
  RunCommand(['git', 'diff', '--quiet', 'HEAD'], env=git_env)
  commit = RunCommand(['git', 'rev-parse', 'HEAD'], stdout=True, env=git_env)
  commit = commit.strip()
  return commit

def Encode(runs, host, bin_path, commit, vid_path):
  records = []

  assert len(commit) == 40

  for run in runs:
    # Prepare
    RunCommand(['rm', '-f', 'opsnr.stt'])

    # Run Encode
    bin = '.'.join([run['runtime_flags'].split(" ")[0], run['config']])
    bin = os.path.join(bin_path, bin)
    run['outfile'] = run['filename'] + ".webm"
    run['infile'] = os.path.join(vid_path, run['filename'])
    cmd = Template(run['runtime_flags']).safe_substitute(run).split(" ")
    cmd[0] = bin
    RunCommand(cmd)

    # Collect Internal Stats
    f = open('opsnr.stt')
    metrics = f.readline().split()
    opsnr = map(float, f.readline().split())
    run_data = dict(zip(metrics, opsnr))

    # CxFPS
    frames = FILES[run['filename']]['frames']
    time_ms = opsnr[-1]
    fps = frames * 1000 / time_ms
    run_data["CxFPS"] = fps

    # Other
    run_data["target_bitrate"] = run['bitrate']

    record = {
      'config_flags': run['configure_flags'],
      'runtime_flags': run['runtime_flags'],
      'commit': commit,
      'config': run['config'],
      'data': {
        run['filename']: [run_data]
      }
    }
    print json.dumps(record, indent=2, sort_keys=True)
    records.append(record)

  # Post to dashboard
  data = {'data': "\n".join([json.dumps(record) for record in records])}
  data = urllib.urlencode(data)
  request = urllib2.Request(METRIC_POST_URL%host, data)
  response = urllib2.urlopen(request)


def UpdateFilesets(host):
  records = []
  for name, params in FILE_SETS.iteritems():
    records.append({'name': name, 'setfiles': params['files']})

  # Post to dashboard
  print records
  data = {'data': "\n".join([json.dumps(record) for record in records])}
  data = urllib.urlencode(data)
  request = urllib2.Request(FILESET_POST_URL%host, data)
  response = urllib2.urlopen(request)


def TriggerBuild(token, commit, args):
  assert len(commit) == 40
  trigger={'parameter': [
    {'name': 'commit', 'value': commit},
    {'name': 'run_params', 'value': " ".join(args)},
  ]}

  data = {'json': json.dumps(trigger), 'token': token}
  data = urllib.urlencode(data)
  request = urllib2.Request(JENKINS_BUILD_URL, data)
  response = urllib2.urlopen(request)


def main(argv):
  # Parse arguments
  options = {"--shard": 0, "--shards": 1, "--src-path": ".", "--bin-path": ".",
             "--vid-path": ".", "--host": "localhost:8080"}
  if "--" in argv:
    opt_end_index = argv.index("--")
  else:
    opt_end_index = len(argv)
  try:
    o, args = getopt.getopt(argv[1:opt_end_index], None, LONG_OPTIONS)
  except getopt.GetoptError, err:
    print str(err)
    Usage(argv[0])
    sys.exit(2)
  options.update(o)

  shard = int(options['--shard'])
  shards = int(options['--shards'])

  if '--build' in options:
    Build(SelectRuns(args, shard, shards),
          src_path=options['--src-path'],
          bin_path=options['--bin-path'])
  elif '--update-filesets' in options:
    UpdateFilesets(host=options['--host'])
  elif '--remote' in options:
    if '--commit' in options:
      commit = options['--commit']
    else:
      commit = GetCommit(src_path=options['--src-path'])
    TriggerBuild(token=options['--token'], commit=commit, args=args)
  else:
    if '--commit' in options:
      commit = options['--commit']
    else:
      commit = GetCommit(src_path=options['--src-path'])
    Encode(SelectRuns(args, shard, shards),
           host=options['--host'],
           bin_path=options['--bin-path'],
           commit=commit,
           vid_path=options['--vid-path'])

if __name__ == "__main__":
  main(sys.argv)
