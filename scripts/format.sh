#!/bin/bash

printf "\nRunning isort...\n"
isort src
printf "\nRunning flake8...\n"
flake8

printf "\nRunning mypy...\n"
mypy src

printf "\nRunning black...\n"
black src --exclude alembic
