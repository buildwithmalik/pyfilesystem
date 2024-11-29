class VirtualDisk:
    """
    Initialize Virtual Disk
    We'll be using a 1 MiB file as our disk.
    """
    def __init__(self, disk_path, total_size_bytes=1024*1024, block_size_bytes=4096):
        self.disk_path = disk_path
        self.total_size_bytes = total_size_bytes
        self.block_size = block_size_bytes
        self.total_blocks = total_size_bytes // block_size_bytes

        # Create disk file if it doesn't exist
        try:
            with open(disk_path, 'rb'):
                print("File already exists")
                pass # File found
        except FileNotFoundError:
            # Create new file
            print("creating new file")
            with open(disk_path, 'wb') as f:
                f.write(b'\0' * total_size_bytes)

        self.bitmap_blocks = 1
        self.initializeBitmap()

    def initializeBitmap(self):
        """
        Create/load the block bitmap
        First block is reserved for bitmap
        Initially all blocks except bitmap block are free
        """
        bitmap = bytearray([0] * self.block_size)
        # block 1 is the bitmap itself so we need to mark it used
        bitmap[0] = 1
        self.write_block(0,bitmap)

    def get_free_block(self):
        """
        Find first free block
        Returns block number or None if disk is full
        """
        bitmap = bytearray(self.read_block(0))
        for blockNum in range(1,self.total_blocks):
            if bitmap[blockNum] == 0:
                return blockNum
            
    def mark_block_free(self, block_number):
        """
        Mark a block as free in bitmap
        """
        bitmap = bytearray(self.read_block(0))
        bitmap[block_number] = 0
        self.write_block(0,bitmap)

    def mark_block_used(self, block_number):
        """
        Mark a block as used in bitmap
        """
        bitmap = bytearray(self.read_block(0))
        bitmap[block_number] = 1
        self.write_block(0,bitmap)

    def is_block_used(self, block_number):
        bitmap = bytearray(self.read_block(0))
        return bitmap[block_number] == 1

    def read_block(self, block_number):
        """
        Read a block from disk
        block_number: which block to read (0-based)
        returns: bytes of block size or None if invalid
        """
        if not 0 <= block_number < self.total_blocks:
            raise ValueError(f"Block number {block_number} out of range")
        
        with open(self.disk_path, 'rb') as f:
            f.seek(block_number * self.block_size)
            return f.read(self.block_size)
        

    def write_block(self, block_number, data):
        """
        Write a block to disk
        block_number: block to write (0-based)
        data: data to write
        """
        if not 0 <= block_number < self.total_blocks:
            raise ValueError(f"Block number {block_number} out of range")
        
        # Pad data with null values if less than block size
        if len(data) < self.block_size:
            data = data + b'\0' * (self.block_size - len(data))
        elif len(data) > self.block_size:
            raise ValueError(f"Data size of {len(data)} exceeds the block size of {self.block_size}")
        
        with open(self.disk_path,'rb+') as f:
            f.seek(block_number * self.block_size)
            f.write(data)

    def delete_block(self, block_number):
        if not 0 <= block_number < self.total_blocks:
            raise ValueError(f"Block number {block_number} out of range")
        
        self.mark_block_free(block_number)

    def get_total_blocks(self):
        return self.total_blocks
    
    def get_block_size(self):
        return self.block_size


# Test the implementation
if __name__ == "__main__":
    # Create a virtual disk with 1MB size and 4KB blocks
    disk = VirtualDisk("test_disk.bin")
    
    # Test writing to a block
    test_data = b"Hello, this is a test!"
    disk.write_block(0, test_data)
    
    # Read back the data
    read_data = disk.read_block(0)
    print(f"Written data: {test_data}")
    print(disk.get_block_size())
    print(disk.get_total_blocks())
    # print(f"Read data: {read_data[:disk.get_block_size()]}")  # Only print the actual data, not padding
    print(f"Read data: {read_data[:len(test_data)]}")  # Only print the actual data, not padding
    
    # Try some error cases
    try:
        disk.write_block(disk.get_total_blocks(), b"This should fail")
    except ValueError as e:
        print(f"Expected error: {e}")
    
    try:
        disk.write_block(0, b"x" * (disk.get_block_size() + 1))
    except ValueError as e:
        print(f"Expected error: {e}")

    # Get a free block
    free_block = disk.get_free_block()
    print(f"Found free block: {free_block}")

    # Mark it as used
    disk.mark_block_used(free_block)
    print(f"Block {free_block} is used: {disk.is_block_used(free_block)}")

    # Mark it as free again
    disk.mark_block_free(free_block)
    print(f"Block {free_block} is used: {disk.is_block_used(free_block)}")
