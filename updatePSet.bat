#!/usr/bin/bash

latex pset.ins && pdflatex pset.dtx && python updateFiles.py