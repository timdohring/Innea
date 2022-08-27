#!/usr/local/bin/python
# provinceCreator.py: Parse a provinces.csv to get all the information into the text file
import csv 
import random

with open('countries.csv', 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    i =0
    #f = open("1.txt", "w+") #country localization
    for row in reader:
        i+=1
        if i >= 788 and i <= 924:
            filename = row['Tag']+" - "+row['Name'] + ".txt"
            f = open(filename, "w+")
            f.write("government = monarchy\nadd_government_reform = feudalism_reform\ngovernment_rank = "+row['Government Rank']+"\n")
            f.write("mercantilism = 10\ntechnology_group = western\n")
            f.write("religion = "+row['Religion']+"\n")
            f.write("primary_culture = "+row['Primary Culture']+"\n")
            f.write("capital = "+row['Capital']+"\n")
            #print('Country code', row['ID'], 'is for', row['Name'])
            
            #country localization
            #f.write(" "+row['Tag']+":0 \""+row['Name']+"\"\n")
            #f.write(" "+row['Tag']+"_ADJ:0 \""+row['Name']+"\"\n")