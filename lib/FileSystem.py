import json
from VirtualDisk import VirtualDisk as VDisk
from Inode import Inode
from typing import List, Dict, Optional

class FileSystem:
    def __init__(self, disk_path:str) -> None:
        self.disk = VDisk(disk_path)
        self.inode_table_block = 1
        self.inodes: Dict[str, Inode.Inode] = {}
        self.load_inode_table()
        self.RESERVED_BLOCKS = {
            0: "bitmap",
            1: "inode_table"
        }
        # First available block for files
        self.FIRST_DATA_BLOCK = max(self.RESERVED_BLOCKS.keys()) + 1

    def load_inode_table(self):
        """Load Inode table from disk"""
        try:
            data = self.disk.read_block(self.inode_table_block)
            json_str = data.decode().rstrip('\0')
            if json_str:
                inode_data = json.loads(json_str)
                self.inodes = {
                    name: Inode.from_dict(data)
                    for name, data in inode_data.items()
                }
        except Exception as e:
            print(f"No Inode table found: {e}")
            self.save_inode_table()

    def save_inode_table(self):
        """Save Inode table to disk"""
        inode_dict = {
            name: inode.to_dict()
            for name, inode in self.inodes.items()
        }
        json_str = json.dumps(inode_dict)
        json_bytes = json_str.encode()
        self.disk.write_block(self.inode_table_block, json_bytes)
        self.disk.mark_block_used(1)

    def create_file(self, name):
        """Create a new file"""
        if name in self.inodes:
            return False
        
        self.inodes[name] = Inode(name)
        self.save_inode_table()
        return True

    def read_file(self, name: str) -> Optional[bytes]:
        """Read data from a file"""
        if name not in self.inodes:
            return None
        inode = self.inodes[name]
        if not inode.blocks:
            return b''

        data = bytearray()
        for physicalBlock in inode.blocks:
            block_data = self.disk.read_block(physicalBlock)

            if len(data) + self.disk.get_block_size() > inode.size:
                remaining = inode.size - len(data)
                data.extend(block_data[:remaining])
            else:
                data.extend(block_data)

        return bytes(data)

    def delete_file(self, name: str) -> bool:
        """Delete a file"""
        if name not in self.inodes:
            return False
        inode = self.inodes[name]

        for block in inode.blocks:
            self.disk.mark_block_free(block)

        del self.inodes[name]
        self.save_inode_table()
        return True
    
    def list_files(self) -> List[Dict]:
        """List all files and their info"""
        return [
            {
                "Name: " : name,
                "Size: " : inode.size,
                "Blocks: " : inode.blocks,
                "Created: " : inode.created_time
            }
            for name, inode in self.inodes.items()
        ]

    def write_file(self, name: str, data: bytes, offset: int = 0) -> bool:
        """Main write function that coordinates the writing process"""
        try:
            inode = self._get_inode(name)
            blocks_needed = self._calculate_blocks_needed(offset, len(data))
            block_mapping = self._ensure_blocks_allocated(inode, blocks_needed)
            self._write_data_to_blocks(data, offset, block_mapping)
            self._update_inode(inode, offset, len(data), block_mapping)
            return True
        except FileNotFoundError as e:
            print(f"Write failed: {e}")
            return False

    def _get_inode(self, name: str) -> Inode:
        """Get inode or raise error if file doesn't exist"""
        if name not in self.inodes:
            raise FileNotFoundError(f"File {name} not found")
        return self.inodes[name]

    def _calculate_blocks_needed(self, offset: int, data_length: int) -> set:
        """Calculate which logical blocks we need for this write"""
        start_block = offset // self.disk.block_size
        end_block = (offset + data_length + self.disk.block_size - 1) // self.disk.block_size
        return set(range(start_block, end_block + 1))

    def _ensure_blocks_allocated(self, inode: Inode, blocks_needed: set) -> dict:
        """Ensure all needed blocks are allocated, return block mapping"""
        block_mapping = {i: block for i, block in enumerate(inode.blocks)}
        
        # Allocate any missing blocks
        for logical_block in blocks_needed:
            if logical_block not in block_mapping:
                new_block = self._allocate_new_block()
                if new_block is None:
                    raise IOError("No free blocks available")
                self.disk.mark_block_used(new_block) 
                block_mapping[logical_block] = new_block
        
        return block_mapping

    def _allocate_new_block(self) -> int:
        """Allocate a new data block"""
        block = self.disk.get_free_block()
        if block is None:
            raise DiskFullError("No free blocks available")
        return block

    def _write_data_to_blocks(self, data: bytes, offset: int, block_mapping: dict):
        
        block_size = self.disk.block_size
        current_offset = offset
        data_offset = 0
        
        while data_offset < len(data):
            logical_block = current_offset // block_size
            block_offset = current_offset % block_size
            
            if logical_block not in block_mapping:
                break
                
            physical_block = block_mapping[logical_block]
            current_block = bytearray(self.disk.read_block(physical_block))
            
            # Calculate how much data we can write to this block
            space_in_block = block_size - block_offset
            data_remaining = len(data) - data_offset
            bytes_to_write = min(space_in_block, data_remaining)
            
            # Write the data
            current_block[block_offset:block_offset + bytes_to_write] = \
                data[data_offset:data_offset + bytes_to_write]
            
            self.disk.write_block(physical_block, bytes(current_block))
            
            current_offset += bytes_to_write
            data_offset += bytes_to_write

    def _get_block_write_info(self, offset: int, remaining_length: int, 
                             block_mapping: dict) -> dict:
        """Calculate information needed for writing to a block"""
        logical_block = offset // self.disk.block_size
        block_offset = offset % self.disk.block_size
        space_in_block = self.disk.block_size - block_offset
        can_write = min(space_in_block, remaining_length)
        
        return {
            'logical_block': logical_block,
            'physical_block': block_mapping[logical_block],
            'block_offset': block_offset,
            'can_write': can_write
        }

    def _write_block_portion(self, physical_block: int, data: bytes, 
                            block_offset: int):
        """Write a portion of data to a specific block"""
        current_block = bytearray(self.disk.read_block(physical_block))
        current_block[block_offset:block_offset + len(data)] = data
        self.disk.write_block(physical_block, bytes(current_block))

    def _update_inode(self, inode: Inode, offset: int, data_length: int, 
                      block_mapping: dict):
        """Update inode with new information"""
        inode.blocks = [block_mapping[i] for i in sorted(block_mapping.keys())]
        inode.size = max(inode.size, offset + data_length)
        self.save_inode_table()

# Add this at the end of filesystem.py

if __name__ == "__main__":
    import os
    
    def print_separator(title):
        print("\n" + "="*50)
        print(title)
        print("="*50)

    # Create a test disk file
    test_disk_path = "test_filesystem.bin"
    if os.path.exists(test_disk_path):
        os.remove(test_disk_path)
    
    # Initialize filesystem
    print_separator("Initializing FileSystem")
    fs = FileSystem(test_disk_path)
    print("FileSystem initialized successfully")

    # Test file creation
    print_separator("Testing File Creation")
    test_files = ["test1.txt", "test2.txt", "test3.txt"]
    for filename in test_files:
        success = fs.create_file(filename)
        print(f"Creating {filename}: {'Success' if success else 'Failed'}")
    
    # Try to create duplicate file
    print("\nTrying to create duplicate file:")
    success = fs.create_file(test_files[0])
    print(f"Creating duplicate file: {'Success' if success else 'Failed (Expected)'}")

    # Test file listing
    print_separator("Testing File Listing")
    files = fs.list_files()
    print("Current files in system:")
    for file_info in files:
        for key, value in file_info.items():
            print(f"{key}{value}")
        print()

    # Test file writing
    print_separator("Testing File Writing")
    test_data = b"Hello, this is test data for our filesystem!"
    success = fs.write_file(test_files[0], test_data)
    print(f"Writing to {test_files[0]}: {'Success' if success else 'Failed'}")

    # Test file reading
    print_separator("Testing File Reading")
    read_data = fs.read_file(test_files[0])
    print(f"Original data: {test_data}")
    print(f"Read data: {read_data}")
    print(f"Data match: {read_data == test_data}")

    # Test file appending
    print_separator("Testing File Appending")
    append_data = b" This is appended data!"
    success = fs.write_file(test_files[0], append_data, offset=len(test_data))
    print(f"Appending to {test_files[0]}: {'Success' if success else 'Failed'}")

    # Read appended file
    read_data = fs.read_file(test_files[0])
    print(f"Full file content: {read_data}")
    print(f"Expected content: {test_data + append_data}")
    print(f"Content match: {read_data == test_data + append_data}")

    # List remaining files
    print("\nRemaining files:")
    files = fs.list_files()
    for file_info in files:
        for key, value in file_info.items():
            print(f"{key}{value}")
        print()

    # Test file deletion
    print_separator("Testing File Deletion")
    for filename in test_files[:2]:  # Delete first two files
        success = fs.delete_file(filename)
        print(f"Deleting {filename}: {'Success' if success else 'Failed'}")

    # List remaining files
    print("\nRemaining files:")
    files = fs.list_files()
    for file_info in files:
        for key, value in file_info.items():
            print(f"{key}{value}")
        print()

    # Test error handling
    print_separator("Testing Error Handling")
    print("1. Reading non-existent file:")
    result = fs.read_file("nonexistent.txt")
    print(f"Result (should be None): {result}")

    print("\n2. Deleting non-existent file:")
    result = fs.delete_file("nonexistent.txt")
    print(f"Result (should be False): {result}")

    print("\n3. Writing to non-existent file:")
    result = fs.write_file("nonexistent.txt", b"This should fail")
    print(f"Result (should be False): {result}")

    # Test large file handling
    print_separator("Testing Large File Handling")
    large_data = b"Large data block " * 1000  # Create ~16KB of data
    fs.create_file("large_file.txt")
    success = fs.write_file("large_file.txt", large_data)
    print(f"Writing large file: {'Success' if success else 'Failed'}")
    
    if success:
        read_large_data = fs.read_file("large_file.txt")
        print(f"Large file size match: {len(read_large_data) == len(large_data)}")
        print(f"Large file content match: {read_large_data == large_data}")

    # Clean up
    print_separator("Cleanup")
    if os.path.exists(test_disk_path):
        os.remove(test_disk_path)
        print(f"Test disk file '{test_disk_path}' removed")

