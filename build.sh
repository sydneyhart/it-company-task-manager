#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

if [[ "${TASKLINE_PUBLIC_DEMO:-0}" == "1" ]]; then
  python manage.py seed_demo \
    --username "${TASKLINE_DEMO_USERNAME:-user}" \
    --password "${TASKLINE_DEMO_PASSWORD:-user12345}"
fi
