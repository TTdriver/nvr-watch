#!/usr/bin/env python3
"""Build a source-only ZIP. Private instance files are never included."""
import argparse,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent
files=['README.md', 'AI-SETUP.md', 'PROJECT_REVIEW.md', 'RELEASE_NOTES.md', 'VERSION', 'server.py', 'exports.py', 'settings.py', 'requirements.txt', 'install.py', 'config.example.json', 'build-package.py', 'server.test.py', 'exports.test.py', 'install.test.py', 'settings.test.py', 'settings-api.test.py', 'container.test.py', 'test.py', 'Dockerfile', 'compose.yaml', 'compose.build.yaml', 'compose.test.yaml', '.dockerignore', '.gitignore', '.env.example', '.github/workflows/container.yaml', 'tests/fake-bi.py', 'web/index.html', 'web/login.html', 'web/login.js', 'web/app.js', 'web/core.js', 'web/core.test.mjs', 'web/package.json', 'web/styles.css', 'web/sample.svg', 'web/settings.html', 'web/settings.js']
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=root.parent/'nvr-watch.zip');args=parser.parse_args()
with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
 for name in files:bundle.write(root/name,'nvr-watch/'+name)
print(args.output)
