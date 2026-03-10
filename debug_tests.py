import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'yelen_school.settings'

import django
django.setup()

from django.test.utils import setup_test_environment, teardown_test_environment
from django.db import connection, connections

try:
    from django.test.runner import DiscoverRunner
    runner = DiscoverRunner(verbosity=2)
    runner.run_tests(['etablissements.tests.test_models'])
except Exception as e:
    import traceback
    traceback.print_exc()
