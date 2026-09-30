import os
import sys

# запускаем blast.py как основной
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "blast.py"), "r", encoding="utf-8") as f:
    code = f.read()

exec(compile(code, "blast.py", "exec"))
