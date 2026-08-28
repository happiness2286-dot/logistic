import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')
print("Đã hợp nhất quy trình! Đang tự động chạy python crawl_and_analyze.py...", flush=True)
subprocess.run([sys.executable, '-u', 'crawl_and_analyze.py'])

