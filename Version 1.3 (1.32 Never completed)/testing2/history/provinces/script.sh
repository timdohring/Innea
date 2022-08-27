#!/bin/bash
# Short script to create a bunch of new textfile for provinces
for i in {5555..5556}; do
    echo -e "add_core = VAR\nowner = VAR\ncontroller = VAR\nculture = swedish\nreligion = catholic\nhre = no\n\nbase_tax = 5\nbase_production = 5\nbase_manpower = 3\n\ntrade_goods = rice\ncapital = \"\"\nis_city = yes\ndiscovered_by = western\n" > "${i} - Innea".txt;
done;