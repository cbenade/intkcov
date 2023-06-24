from os import getcwd, listdir, remove, path
import sys
import csv
import re
from math import floor


# Get current working directory as global
cwd = getcwd()

####################################################################################
# Define main
####################################################################################
def main():

    # Check for proper usage
    if len(sys.argv) != 1:
        sys.exit("Usage: python3 covanalysis.py")

    if combineRawData():
        if filterCombinedRawData():
            if findCylinderPairs():
                if getWeeklyPairData():
                    if generateWeeklyPairDataSummary():
                        deleteHelperFiles()


####################################################################################
# Copy contents of daily RawData to CombinedRawData
####################################################################################
def combineRawData():
    # Copy header from first file only for writer
    write_name = path.join(cwd, "CombinedRawData.CSV")
    f_write = open(write_name, "w")
    writer = csv.writer(f_write)
    first_file = True

    # Copy contents of CSV to new file using writer
    for file in listdir(path.join(cwd, "RawData")):
        if file.endswith(".CSV"):
            read_name = path.join(cwd, "RawData", file)
            f_read = open(read_name, "r")
            reader = csv.reader(f_read)

            past_garbage = False
            for line in reader:
                # Skip past initial garbage lines
                if past_garbage == False:
                    if len(line) != 0:
                        if line[0] == "Lab No":
                            past_garbage = True
                            if first_file == True:
                                first_file = False
                                writer.writerow(line)
                # Once past garbage
                else:
                    writer.writerow(line)
            f_read.close

    f_write.close
    return True


####################################################################################
# Filter contents of CombinedRawData to CombinedFilteredData
####################################################################################
def filterCombinedRawData():
    # CombinedRawData reader
    read_name = path.join(cwd, "CombinedRawData.CSV")
    f_read = open(read_name, "r")
    reader = csv.DictReader(f_read)

    # CombinedFilteredData writer
    write_name = path.join(cwd, "CombinedFilteredData.CSV")
    f_write = open(write_name, "w")
    writer_fieldnames = [
        "Lab No",
        "Age (Days)",
        "Test Date",
        "Strength (MPa)",
        "Marks"]
    writer = csv.DictWriter(f_write, fieldnames=writer_fieldnames)

    # Regular expression object
    labnoRegex = re.compile(r"^755-(\d\d)-(\d\d\d)-(\d)+-C(\d)+([A-Z])$")

    # Write CombinedFilteredData file
    writer.writeheader()
    for row in reader:
        filteredData = {}
        filteredData["Lab No"] = row["Lab No"]
        filteredData["Age (Days)"] = row["Age (Days)"]
        filteredData["Test Date"] = row["Test Date"]
        filteredData["Strength (MPa)"] = row["Strength (MPa)"]
        filteredData["Marks"] = row["Marks"]

        if row["Reqd Strength"] != '':
            reqstrength = str(round(float(row["Reqd Strength"]), 1))

        match = re.match(labnoRegex, filteredData["Lab No"])
        if (
            match != None
            and not (match.group(1) == "18" and match.group(2) == "015")
            and not (int(float(reqstrength)) < 5)
            and not int(filteredData["Age (Days)"]) < 28
            and not filteredData["Marks"] == "FC"
        ):
            writer.writerow(filteredData)

    f_read.close
    f_write.close
    return True


####################################################################################
# Find coupled cylinders in CombinedFilteredData, copy to RawPairData
####################################################################################
def findCylinderPairs():
    # CombinedRawData reader
    read_name = path.join(cwd, "CombinedFilteredData.CSV")
    f_read = open(read_name, "r")
    reader = csv.DictReader(f_read)

    # CombinedFilteredData writer
    write_name = path.join(cwd, "RawPairData.CSV")
    f_write = open(write_name, "w")
    writer_fieldnames = [
        "Break Date",
        "SAMPLE ID",
        "AGE (days)",
        "HIGH VALUE (MPa)",
        "LOW VALUE (MPa)",
        "AVERAGE (MPa)",
        "DELTA (MPa)",
        "COV",
        "MARKS"]
    writer = csv.DictWriter(f_write, fieldnames=writer_fieldnames)

    # Create dictionary of cylinders using reader
    cylinder_list = []
    for row in reader:
        cylinder_list.append(row)

    # Find cylinder partners and copy data to dictionary
    pair_sets = set()
    pair_data = []

    for cylinder in cylinder_list:
        if cylinder["Lab No"][:-1] in pair_sets:
            continue
        else:
            matchCount = 0
            labnoRegex = re.compile(cylinder["Lab No"][:-1])
            highStrength = 0
            lowStrength = 10000

        for partner in cylinder_list:
            match = re.match(labnoRegex, partner["Lab No"][:-1])

            if (
                match != None
                and cylinder["Test Date"] == partner["Test Date"]
                and cylinder["Marks"] == partner["Marks"]
                and not (cylinder["Strength (MPa)"] == '' or partner["Strength (MPa)"] == '')
            ):
                matchCount += 1
                testDate = partner["Test Date"]
                sampleID = partner["Lab No"][:-1]
                age = partner["Age (Days)"]
                cylinderStrength = float(partner["Strength (MPa)"])
                if cylinderStrength > highStrength:
                    highStrength = cylinderStrength
                if cylinderStrength < lowStrength:
                    lowStrength = cylinderStrength
                marks = partner["Marks"]
                pair_sets.add(sampleID)

        if matchCount >= 2:
            if matchCount == 2:
                constant = 0.866
            elif matchCount == 3:
                constant = 0.591
            else:
                continue
            pairedData = {}
            pairedData["Break Date"] = testDate
            pairedData["SAMPLE ID"] = sampleID
            pairedData["AGE (days)"] = age
            pairedData["HIGH VALUE (MPa)"] = highStrength
            pairedData["LOW VALUE (MPa)"] = lowStrength
            pairedData["AVERAGE (MPa)"] = str(round(((highStrength + lowStrength) / 2), 2))
            pairedData["DELTA (MPa)"] = str(round(abs(highStrength - lowStrength), 1))
            pairedData["COV"] = str(round((float(pairedData["DELTA (MPa)"]) * constant * 100) / float(pairedData["AVERAGE (MPa)"]), 2)) + "%"
            pairedData["MARKS"] = marks
            pair_data.append(pairedData)

    # Write results to write file
    writer.writeheader()
    sorted_pair_list = sorted(pair_data, key=lambda pair_data: (pair_data['Break Date'], pair_data['SAMPLE ID']))
    for pair in sorted_pair_list:
        writer.writerow(pair)

    f_read.close
    f_write.close
    return True


####################################################################################
# Generate weekly paired data using RawPairData
####################################################################################
def getWeeklyPairData():
    # Reader
    read_name = path.join(cwd, "RawPairData.CSV")
    f_read = open(read_name, "r")
    reader = csv.DictReader(f_read)

    # Writer
    write_name = path.join(cwd, "WeeklyPairData2021.CSV")
    f_write = open(write_name, "w")
    writer_fieldnames = ["WEEK"]
    for fieldname in reader.fieldnames:
        writer_fieldnames.append(fieldname)
    writer = csv.DictWriter(f_write, fieldnames=writer_fieldnames)

    new_pair_list = []
    for row in reader:
        temp = {}
        date = row["Break Date"]
        num = int(swapDateFormat(date))
        week = str(floor((num - 1) / 7) + 1)
        temp["WEEK"] = week
        for item in row:
            temp[item] = row.get(item)
        new_pair_list.append(temp)

    # Write results to write file
    writer.writeheader()
    new_sorted_pair_list = sorted(new_pair_list, key=lambda new_pair_list: (new_pair_list['WEEK'], new_pair_list['Break Date'], new_pair_list['SAMPLE ID']))
    for pair in new_sorted_pair_list:
        writer.writerow(pair)

    f_read.close
    f_write.close
    return True

# Helper function that converts MM/DD to number
def swapDateFormat(date):
    # Regular expression object
    dateRegex = re.compile(r"^(\d\d)/(\d\d)$")
    match = re.match(dateRegex, date)

    if match != None:
        # date is MM/DD, month_conversion currently adjusted for 2021 (non-leap year)
        # if leap year, add 1 to every month from 03-12 (inclusive)
        month_conversion = {
            "01": 0,
            "02": 31,
            "03": 59,
            "04": 90,
            "05": 120,
            "06": 151,
            "07": 181,
            "08": 212,
            "09": 243,
            "10": 273,
            "11": 304,
            "12": 334
        }
        # Returns date as a number
        return str(month_conversion.get(match.group(1)) + int(match.group(2)))
    else:
        # date is ###
        return "improper date format"


####################################################################################
# Generate weekly paired data summary using WeeklyPairData2021
####################################################################################
def generateWeeklyPairDataSummary():
    # Reader
    read_name = path.join(cwd, "WeeklyPairData2021.CSV")
    f_read = open(read_name, "r")
    reader = csv.DictReader(f_read)

    # Writer
    write_name = path.join(cwd, "WeeklyPairDataSummary2021.CSV")
    f_write = open(write_name, "w")
    writer_fieldnames = [
        "WEEK",
        "# OF TESTS",
        "# OF COEFF > 10%",
        "AVG COV",
        "MOVING 5 WEEK AVG",
        "RATING"
    ]
    writer = csv.DictWriter(f_write, fieldnames=writer_fieldnames)

    # Copy contents of reader into summaryDict
    summaryDictList = []
    for row in reader:
        summaryDictList.append(row)

    # Copy results into resultsDict
    resultsDictList = []
    for week in range(1,53):
        resultEntry = {}
        numGreaterThan = 0
        numOfTests = 0
        covSum = 0

        for pair in summaryDictList:
            if week == int(float(pair["WEEK"])):
                cov = float(pair["COV"].rstrip("%"))
                if cov > 10:
                    numGreaterThan += 1
                numOfTests += 1
                covSum += cov

        if numOfTests != 0:
            resultEntry["WEEK"] = week
            resultEntry["# OF TESTS"] = numOfTests
            resultEntry["# OF COEFF > 10%"] = numGreaterThan
            resultEntry["AVG COV"] = covSum / numOfTests
            resultsDictList.append(resultEntry)

    # Calculate 5 week moving average data and add into resultsDictList dictionaries
    for i in range(len(resultsDictList)):
        movingNumOfTests = 0
        movingSum = 0

        if i < 4:
            for j in range(i + 1):
                movingNumOfTests += resultsDictList[j]["# OF TESTS"]
                movingSum += resultsDictList[j]["AVG COV"] * resultsDictList[j]["# OF TESTS"]
            if movingNumOfTests != 0:
                resultsDictList[i]["MOVING 5 WEEK AVG"] = movingSum / movingNumOfTests
        else:
            for j in range(5):
                movingNumOfTests += resultsDictList[i - j]["# OF TESTS"]
                movingSum += resultsDictList[i - j]["AVG COV"] * resultsDictList[i - j]["# OF TESTS"]
            if movingNumOfTests != 0:
                resultsDictList[i]["MOVING 5 WEEK AVG"] = movingSum / movingNumOfTests

        if movingNumOfTests == 0:
            resultsDictList[i]["MOVING 5 WEEK AVG"] = 0

    # Add moving 5 week average rating to resultsDictList, then format coefficients
    for i in range(len(resultsDictList)):
        if resultsDictList[i]["# OF COEFF > 10%"] == 0 and resultsDictList[i]["MOVING 5 WEEK AVG"] <= 5:
            resultsDictList[i]["RATING"] = "satisfactory"
        else:
            resultsDictList[i]["RATING"] = "unsatisfactory"

        resultsDictList[i]["AVG COV"] = str(round(resultsDictList[i]["AVG COV"], 2)) + "%"
        resultsDictList[i]["MOVING 5 WEEK AVG"] = str(round(resultsDictList[i]["MOVING 5 WEEK AVG"], 2)) + "%"

    # Write summary data to WeeklyPairDataSummary2021
    writer.writeheader()
    for result in resultsDictList:
        writer.writerow(result)

    f_read.close
    f_write.close
    return True


####################################################################################
# Delete helper files from directory
####################################################################################
def deleteHelperFiles():
    # Delete helper files
    helperFiles = [
        "CombinedRawData.CSV",
        "CombinedFilteredData.CSV",
        "RawPairData.CSV"
    ]
    for file in listdir(cwd):
        if file.endswith(".CSV") and file in helperFiles:
            remove(file)


####################################################################################
# Run main
####################################################################################
if __name__ == "__main__":
    main()
