#!/usr/bin/env python3
import time
import sys
import json

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 sleep_script.py <seconds>")
        sys.exit(1)
    
    try:
        seconds = int(sys.argv[1])
    except ValueError:
        print("Error: seconds must be an integer")
        sys.exit(1)
    
    if seconds < 0:
        print("Error: seconds must be non-negative")
        sys.exit(1)
    
    print(f"Python script: sleeping for {seconds} seconds")
    
    # 1秒毎に進捗率をJSONで出力
    for i in range(seconds + 1):
        progress = (i / seconds) * 100 if seconds > 0 else 100
        progress_data = {
            "elapsed_seconds": i,
            "total_seconds": seconds,
            "progress_percentage": round(progress, 2),
            "remaining_seconds": seconds - i,
            "status": "completed" if i == seconds else "running"
        }
        print(json.dumps(progress_data, ensure_ascii=False))
        
        if i < seconds:
            time.sleep(1)
    
    print(f"Python script: finished sleeping for {seconds} seconds")

if __name__ == "__main__":
    main()
