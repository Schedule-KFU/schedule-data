import os
from base_curriculum_parser import run_curriculum_crawler

FACULTY_ID = 6
FACULTY_NAME = "Институт физики"
OUTPUT_FILE = "curriculum_physics.json"

def run_parser():
    run_curriculum_crawler(FACULTY_ID, FACULTY_NAME, OUTPUT_FILE)

if __name__ == "__main__":
    run_parser()
