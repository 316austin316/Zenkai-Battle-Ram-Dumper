import os
import core.utils as ut

class STPK:
    header_size = 16
    entry_size = 48

    def __init__(self):
        self.entries = []

    def read(self, stream):
        self.start_offset = stream.tell()
        stream.seek(8, os.SEEK_CUR) # skip unknown bytes
        entry_count = ut.b2i(stream.read(4))
        stream.seek(4, os.SEEK_CUR) # skip unknown bytes
        self.entries_offset = self.start_offset + self.header_size

        for i in range(entry_count):
            stream.seek(self.entries_offset + (i * self.entry_size))
            data_offset = ut.b2i(stream.read(4))
            data_size = ut.b2i(stream.read(4))
            stream.seek(8, os.SEEK_CUR) # skip unknown bytes
            data_name = ut.read_string(stream, 32, 32)

            entry_object = STPKEntry(data_name, data_size)
            entry_object.offset = self.start_offset + data_offset
            entry_object.read(stream, self.start_offset + data_offset)

            self.entries.append(entry_object)


    def write(self, stream):
        # Writing header
        self.start_offset = stream.tell()
        stream.write(ut.s2b_name(type(self).__name__))  # Corrected here
        stream.write(ut.i2b(1))  # write unknown bytes
        stream.write(ut.i2b(len(self.entries)))
        stream.write(ut.i2b(self.header_size))

        stream.write(bytes(self.entry_size * len(self.entries)))
        stream.write(bytes(16))  # Add 16-byte padding

        self.write_data(stream)

        # Writing entries info
        stream.seek(self.start_offset + self.header_size)
        for entry in self.entries:
            stream.write(ut.i2b(entry.offset - self.start_offset))
            size = entry.size  # Directly use size attribute
            stream.write(ut.extb(ut.i2b(size), 12))
            stream.write(ut.extb(entry.name, 32))
            
    def write_data(self, stream):
        for entry in self.entries:
            # Assuming the data offset is calculated from the start of the file
            stream.seek(entry.offset)
            stream.write(entry.data)

class STPKEntry():
    def __init__(self, name, size):
        self.name = name
        self.size = size

    def read(self, stream, start_offset):
        stream.seek(start_offset)
        self.data = stream.read(self.size)

    def write(self, stream):
        stream.seek(self.offset)
        stream.write(self.data)

