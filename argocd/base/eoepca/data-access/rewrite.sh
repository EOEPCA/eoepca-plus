#!/bin/bash

# Read from stdin
cat - | sed 's/develop.eoepca.org/test-vcluster.develop.eoepca.org/g'