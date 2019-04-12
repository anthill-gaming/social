#!/usr/bin/env bash

# Setup postgres database
createuser -d anthill_social -U postgres
createdb -U anthill_social anthill_social