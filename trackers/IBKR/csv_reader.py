import csv

class CsvReader:
    def __init__(self, filePath):
        self.filePath = filePath

    def read_rows(self):
        with open(self.filePath, newline="") as csvfile:
            return list(csv.DictReader(csvfile))