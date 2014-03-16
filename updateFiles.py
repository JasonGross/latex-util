#!/usr/bin/python
from FileUpdater import *

def UpdateFiles():
    for file_name in ('header.tex', 'pset.dtx', 'pset.cls', 'pset.ins'):
        ask_update_files(file_name)
    consolidate_files()
    cleanup_files()
    cleanup_more_files()

if __name__ == '__main__':
    UpdateFiles()

