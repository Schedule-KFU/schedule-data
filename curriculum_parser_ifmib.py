import os
from base_curriculum_parser import run_curriculum_crawler

FACULTY_ID = 8494
FACULTY_NAME = "Институт фундаментальной медицины и биологии"
OUTPUT_FILE = "curriculum_ifmib.json"

def run_parser():
    run_curriculum_crawler(FACULTY_ID, FACULTY_NAME, OUTPUT_FILE)

if __name__ == "__main__":
    run_parser()
