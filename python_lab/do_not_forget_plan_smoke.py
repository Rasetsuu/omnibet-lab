#!/usr/bin/env python3
from pathlib import Path
import json
cfg = json.loads(Path('configs/do_not_forget_plan_v521.json').read_text())
assert cfg['advanced_tools_hidden_by_default'] is True
print('ok')
