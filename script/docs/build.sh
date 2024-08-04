#!/bin/bash

cd $(dirname $(dirname  $(dirname $0)))

exec sphinx-build -M html docs build/sphinx/ "$@"
