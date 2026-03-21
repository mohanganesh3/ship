#!/bin/bash
cd /Users/mohanganesh/ship/maritime_pipeline
echo "Running PDF extractor..."
/opt/anaconda3/bin/python extraction/pdf_extractor.py 2>&1 | tail -10
echo "Done."
