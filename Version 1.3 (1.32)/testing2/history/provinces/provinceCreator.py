#!/usr/local/bin/python
# provinceCreator.py: Parse a provinces.csv to get all the information into the text file
import csv 

with open('provinces.csv', 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if int(row['ID']) >= 4150 and int(row['ID']) <= 4907:
            filename = row['ID'] + " - Innea.txt"
            f = open(filename, "w+")
            if row['Owner'] != '':
                f.write("add_core = "+row['Owner']+"\nowner = "+row['Owner']+"\ncontroller = "+row['Owner']+"\nculture = "+row['Culture']+"\nreligion = "+row['Religion']+"\nhre = no\n\n")
            else:
                f.write("culture = "+row['Culture']+"\nreligion = "+row['Religion']+"\nhre = no\n\n")
            f.write("base_tax = "+row['Tax']+"\nbase_production = "+row['Production']+"\nbase_manpower = "+row['Manpower']+"\n\n")
            f.write("trade_goods = "+row['Trade Good']+"\ncapital = \""+row['Capital']+"\"\nis_city = yes\ndiscovered_by = western\n")
            #print('Country code', row['ID'], 'is for', row['Name'])