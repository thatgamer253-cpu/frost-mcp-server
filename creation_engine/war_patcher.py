"""
Kinetic Council - WAR-64.exe Binary Patcher
Target: Return of Reckoning (1.4.8+)
Engine: Gamebryo
Path: 0x00613B00 (Lua Stack Check)

Fixes:
1. Lua C Stack Overflow Limit: 200 -> 400
   - Prevents UI crashes in heavy RvR sieges
2. Secondary recursion safety check: 224 -> 448
   - Allows deeper addon execution chains

Author: Kinetic Council
"""

import struct
import shutil
import os
import hashlib
from datetime import datetime

class WarPatcher:
    def __init__(self, exe_path):
        self.exe_path = exe_path
        self.backup_path = exe_path + ".zenith.bak"
        self.patches_applied = []
        
        # Read binary
        with open(exe_path, 'rb') as f:
            self.data = bytearray(f.read())
        
        self.original_hash = hashlib.md5(self.data).hexdigest()
        print(f"Loaded: {exe_path}")
        print(f"Size: {len(self.data)} bytes")
        print(f"MD5: {self.original_hash}")
        
        # WAR-64.exe is 32-bit (despite name), base is likely 0x00400000
        self.image_base = 0x00400000
    
    def _va_to_offset(self, virtual_address):
        return virtual_address - self.image_base
    
    def backup(self):
        if not os.path.exists(self.backup_path):
            shutil.copy2(self.exe_path, self.backup_path)
            print(f"Backup created: {self.backup_path}")
    
    def apply_lua_stack_fix(self):
        print("\n=== PATCH: Lua C Stack Overflow Limit (200 -> 400) ===")
        
        # Function FUN_00613b00
        # Based on decompilation, the check is early in the function
        # Look for CMP AX, 200 (66 3D C8 00)
        
        func_va = 0x00613b00
        offset = self._va_to_offset(func_va)
        
        # Scan first 64 bytes of function for the pattern
        func_bytes = self.data[offset:offset+64]
        
        # Pattern 1: CMP AX, 200 (66 3D C8 00)
        pattern1 = bytes([0x66, 0x3D, 0xC8, 0x00])
        idx1 = func_bytes.find(pattern1)
        
        if idx1 >= 0:
            patch_offset = offset + idx1
            print(f"  Found 'CMP AX, 200' at VA 0x{func_va + idx1:08X}")
            print(f"  Old: {pattern1.hex()}")
            
            # Patch to 400 (0x0190) -> 66 3D 90 01
            new_bytes = bytes([0x66, 0x3D, 0x90, 0x01])
            self.data[patch_offset:patch_offset+4] = new_bytes
            print(f"  New: {new_bytes.hex()}")
            self.patches_applied.append("Lua Stack Base Limit (200->400)")
        else:
            print("  [ERROR] Pattern 1 not found!")
            print(f"  First 32 bytes: {func_bytes[:32].hex()}")
            
        # Pattern 2: CMP AX, 224 (0xE0) - Secondary Check
        # 66 3D E0 00
        pattern2 = bytes([0x66, 0x3D, 0xE0, 0x00])
        idx2 = func_bytes.find(pattern2)
        
        if idx2 >= 0:
            patch_offset = offset + idx2
            print(f"  Found 'CMP AX, 224' at VA 0x{func_va + idx2:08X}")
            print(f"  Old: {pattern2.hex()}")
            
            # Patch to 448 (0x01C0) -> 66 3D C0 01
            new_bytes = bytes([0x66, 0x3D, 0xC0, 0x01])
            self.data[patch_offset:patch_offset+4] = new_bytes
            print(f"  New: {new_bytes.hex()}")
            self.patches_applied.append("Lua Stack Secondary Limit (224->448)")
        else:
            print("  [ERROR] Pattern 2 not found!")

    def save(self):
        if self.patches_applied:
            with open(self.exe_path, 'wb') as f:
                f.write(self.data)
            print(f"\nSaved patched binary to: {self.exe_path}")
            print(f"Patches applied: {len(self.patches_applied)}")
            new_hash = hashlib.md5(self.data).hexdigest()
            print(f"New MD5: {new_hash}")
        else:
            print("\nNo patches applied. File unchanged.")

def main():
    target = r"C:\Users\thatg\Desktop\Modernize\WAR-64.exe"
    if not os.path.exists(target):
        print(f"Target not found: {target}")
        return
        
    patcher = WarPatcher(target)
    patcher.backup()
    patcher.apply_lua_stack_fix()
    patcher.save()

if __name__ == "__main__":
    main()
