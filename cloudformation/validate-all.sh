#!/bin/bash
dir=$(dirname $0)
for file in $dir/*.json; do
    echo "validating" $file
    aws cloudformation validate-template --template-body file://$file
done
