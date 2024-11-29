import unittest
import os
from lib.VirtualDisk import VirtualDisk

class TestVirtualDisk(unittest.TestCase):
    def setUp(self):
        self.disk_path = "test_disk.bin"
        self.disk = VirtualDisk(self.disk_path)

    def tearDown(self):
        # Clean up the test file
        if os.path.exists(self.disk_path):
            os.remove(self.disk_path)

    def test_disk_creation(self):
        self.assertTrue(os.path.exists(self.disk_path))
        self.assertEqual(os.path.getsize(self.disk_path), 1024*1024)  # 1MB

    def test_write_and_read_block(self):
        test_data = b"Test data"
        self.disk.write_block(0, test_data)
        read_data = self.disk.read_block(0)
        self.assertEqual(read_data[:len(test_data)], test_data)

    def test_multiple_blocks(self):
        # Write to multiple blocks and read back
        data1 = b"First block"
        data2 = b"Second block"
        
        self.disk.write_block(0, data1)
        self.disk.write_block(1, data2)
        
        self.assertEqual(self.disk.read_block(0)[:len(data1)], data1)
        self.assertEqual(self.disk.read_block(1)[:len(data2)], data2)

    def test_invalid_block_number(self):
        with self.assertRaises(ValueError):
            self.disk.read_block(-1)
        with self.assertRaises(ValueError):
            self.disk.read_block(self.disk.get_total_blocks())

    def test_oversized_data(self):
        oversized_data = b"x" * (self.disk.get_block_size() + 1)
        with self.assertRaises(ValueError):
            self.disk.write_block(0, oversized_data)

if __name__ == '__main__':
    unittest.main()