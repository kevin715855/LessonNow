import subprocess
import sys
from connect import connect_to_chrome

def run(script):

    result = subprocess.run(
        [sys.executable, script]
    )

    if result.returncode != 0:
        raise SystemExit(
            f"{script} failed"
        )
    
'''
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
--remote-debugging-port=9222 `
--user-data-dir="$PWD\chrome_profile"
'''

def main():
    print("STEP 1: Connect to roadmap.sh")
    connect_to_chrome()

    print("STEP 2: Fetch lessons")
    run("get_api.py")

    print()
    print("STEP 3: Convert to Markdown")
    run("markdown.py")

    print()
    print("DONE")

if __name__ == "__main__":
    main()