import traceback
import sys

def run():
    with open('test_output.txt', 'r', encoding='utf-16', errors='replace') as f:
        print(f.read())
        
if __name__ == '__main__':
    run()
