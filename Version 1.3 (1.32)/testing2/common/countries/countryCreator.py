#!/usr/local/bin/python
# provinceCreator.py: Parse a provinces.csv to get all the information into the text file
import csv 
import random

with open('countries.csv', 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    i =0
    for row in reader:
        i+=1
        if i >= 999 and i <= 999:
            filename = row['Name'] + ".txt"
            f = open(filename, "w+")
            f.write("#Country Name: Please see filename.\n\ngraphical_culture = westerngfx\n\n")
            a = random.randint(0, 255)
            b = random.randint(0, 255)
            c = random.randint(0, 255)
            f.write("color = { "+str(a)+" "+str(b)+" "+str(c)+"}\n\n#revolutionary_colors = { 8 1 8 }\n\n")
            f.write("historical_idea_groups = {\n\tdefensive_ideas\n\toffensive_ideas\n\treligious_ideas\n\teconomic_ideas\n\tdiplomatic_ideas\n\tinnovativeness_ideas\n\tspy_ideas\n\ttrade_ideas\n}\n\n")
            f.write("historical_units = {\n\twestern_medieval_infantry\n\twestern_medieval_knights\n\twestern_men_at_arms\n\tswiss_landsknechten\n\tdutch_maurician\n\taustrian_tercio\n\taustrian_grenzer\n\taustrian_hussar\n\taustrian_white_coat\n\tprussian_uhlan\n\taustrian_jaeger\n\tmixed_order_infantry\n\topen_order_cavalry\n\tnapoleonic_square\n\tnapoleonic_lancers\n}\n\n")
            f.write("monarch_names = {\n\n}\n\nleader_names = {\n\n}\n\nship_names = {\n\n}\n\n")
            f.write("monarch_names = {\n\t\"Army of $PROVINCE$\"\n}\n\nfleet_names = {\n\n}\n")
            #print('Country code', row['ID'], 'is for', row['Name'])