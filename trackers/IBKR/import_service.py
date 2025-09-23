from .csv_reader import CsvReader
from .option_mapper import OptionMapper
from .option_saver import OptionSaver


class OptionImportService:
    def __init__(self, filepath, user):
        self.reader = CsvReader(filepath)
        self.mapper = OptionMapper()
        self.saver = OptionSaver(user)

    def run(self):
        rows = self.reader.read_rows()
        for row in rows:
            if row["DataDiscriminator"] != "Order":
                continue  # Skip headers or non-trade lines
            data = self.mapper.parse_option_string(row["Symbol"])
            self.saver.save(row, data)
            print(row)
