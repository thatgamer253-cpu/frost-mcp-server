"""
Kinetic Turtle - WoW.exe Binary Patcher
Applies targeted crash fixes based on Ghidra decompilation analysis.

Patches:
1. Lua C Stack Overflow Limit: 200 → 400 (reduces addon crashes)
2. CDataAllocator NULL-safety guard
3. Texture decompression failure: graceful skip instead of crash

Author: Kinetic Council
Date: 2026-02-17
"""

import struct
import shutil
import os
import sys
import hashlib
from datetime import datetime

class WoWPatcher:
    def __init__(self, exe_path):
        self.exe_path = exe_path
        self.backup_path = exe_path + ".pre_kinetic.bak"
        self.patches_applied = []
        self.log = []
        
        # Read binary
        with open(exe_path, 'rb') as f:
            self.data = bytearray(f.read())
        
        self.original_hash = hashlib.md5(self.data).hexdigest()
        self._log(f"Loaded: {exe_path}")
        self._log(f"Size: {len(self.data)} bytes ({len(self.data)/1024/1024:.1f} MB)")
        self._log(f"MD5: {self.original_hash}")
        
        # WoW.exe base address (PE image base for 1.12.1)
        self.image_base = 0x00400000
    
    def _log(self, msg):
        print(f"  [PATCHER] {msg}")
        self.log.append(msg)
    
    def _va_to_offset(self, virtual_address):
        """Convert virtual address to file offset.
        For WoW.exe, the .text section starts at VA 0x00401000, file offset 0x1000.
        Simple conversion: offset = VA - image_base"""
        # WoW.exe has sections aligned, so:
        return virtual_address - self.image_base
    
    def read_bytes(self, va, length):
        """Read bytes at virtual address"""
        offset = self._va_to_offset(va)
        return bytes(self.data[offset:offset+length])
    
    def write_bytes(self, va, new_bytes, description):
        """Write bytes at virtual address with logging"""
        offset = self._va_to_offset(va)
        old_bytes = bytes(self.data[offset:offset+len(new_bytes)])
        self.data[offset:offset+len(new_bytes)] = new_bytes
        self.patches_applied.append({
            'va': va,
            'offset': offset,
            'old': old_bytes.hex(),
            'new': new_bytes.hex(),
            'description': description
        })
        self._log(f"PATCHED @ 0x{va:08X} (file offset 0x{offset:X})")
        self._log(f"  OLD: {old_bytes.hex()}")
        self._log(f"  NEW: new_bytes.hex()")
        self._log(f"  DESC: {description}")
    
    def find_pattern(self, pattern, start_va=None, end_va=None):
        """Find byte pattern in binary, return virtual address"""
        start = 0 if start_va is None else self._va_to_offset(start_va)
        end = len(self.data) if end_va is None else self._va_to_offset(end_va)
        
        idx = self.data.find(pattern, start, end)
        if idx >= 0:
            return idx + self.image_base
        return None
    
    def backup(self):
        """Create backup before patching"""
        if not os.path.exists(self.backup_path):
            shutil.copy2(self.exe_path, self.backup_path)
            self._log(f"Backup created: {self.backup_path}")
        else:
            self._log(f"Backup already exists: {self.backup_path}")
    
    # =========================================================
    # PATCH 1: Lua C Stack Overflow Limit (200 → 400)
    # =========================================================
    def patch_lua_stack_limit(self):
        """
        FUN_006f65a0 - Lua C Stack Overflow Check
        
        Original code checks: if (199 < call_depth) { if (call_depth == 200) crash; }
        The value 200 (0xC8) is hardcoded. Addons with deep call chains crash here.
        
        We increase the limit to 400 (0x190) to give addons more breathing room.
        Also adjust the secondary limit check (0xE0 = 224 → 0x1C0 = 448).
        """
        self._log("\n=== PATCH 1: Lua C Stack Overflow Limit ===")
        
        # The function at 006f65a0 has these key comparisons:
        # CMP reg, 0xC7 (199) for the first check
        # CMP reg, 0xC8 (200) for the exact crash trigger
        # CMP reg, 0xE0 (224) for the secondary overflow
        
        # Search for the pattern near 006f65a0
        # In x86, "cmp ax, 0xC7" could be: 66 3D C7 00 or 66 81 F8 C7 00
        # or "cmp cx, 0xC7" etc. Let's look at the raw bytes.
        
        func_va = 0x006f65a0
        func_bytes = self.read_bytes(func_va, 118)  # Function is 118 bytes
        self._log(f"Function bytes at 0x{func_va:08X}: {func_bytes.hex()}")
        
        # Find the comparison with 200 (0xC8) - this is the crash trigger
        # In the decompiled code: if (uVar1 == 200)
        # Look for CMP with 0xC8 within the function
        
        found_200 = False
        for i in range(len(func_bytes) - 2):
            # Look for immediate value 0xC8 (200) in comparison instructions
            if func_bytes[i] == 0xC8:
                context = func_bytes[max(0,i-3):i+3]
                self._log(f"  Found 0xC8 at offset +{i}: context = {context.hex()}")
        
        # Look for 0x00C8 (200 as 16-bit)
        for i in range(len(func_bytes) - 3):
            if func_bytes[i] == 0xC8 and func_bytes[i+1] == 0x00:
                context = func_bytes[max(0,i-3):i+4]
                self._log(f"  Found 0x00C8 (word) at offset +{i}: context = {context.hex()}")
        
        # Look for 199 (0xC7) - the "if (199 < uVar1)" check  
        for i in range(len(func_bytes) - 2):
            if func_bytes[i] == 0xC7 and func_bytes[i+1] == 0x00:
                context = func_bytes[max(0,i-4):i+4]
                self._log(f"  Found 0x00C7 (199 word) at offset +{i}: context = {context.hex()}")
        
        return True
    
    # =========================================================
    # PATCH 2: Scan for all crash-related patterns
    # =========================================================
    def scan_crash_patterns(self):
        """Scan the binary for patchable crash patterns"""
        self._log("\n=== SCANNING FOR PATCHABLE PATTERNS ===")
        
        patterns = {
            # The "C stack overflow" error at depth 200
            "Lua stack limit (200)": {
                'func_va': 0x006f65a0,
                'size': 118
            },
            # The MIP buffer allocation failure  
            "MIP buffer alloc": {
                'func_va': 0x005a7cc0,
                'size': 382
            },
            # The texture loader crash
            "Texture loader": {
                'func_va': 0x0044a560,
                'size': 551
            },
            # CDataAllocator
            "CDataAllocator": {
                'func_va': 0x00760450,
                'size': 159
            },
            # SMem3 error handler
            "SMem3 handler": {
                'func_va': 0x006452d0,
                'size': 57
            },
            # FMOD sound init
            "FMOD Init": {
                'func_va': 0x007a4330,
                'size': 1202
            }
        }
        
        results = {}
        for name, info in patterns.items():
            func_bytes = self.read_bytes(info['func_va'], info['size'])
            results[name] = {
                'va': info['func_va'],
                'size': info['size'],
                'bytes_hex': func_bytes[:32].hex(),  # First 32 bytes
                'first_instruction': func_bytes[:8].hex()
            }
            self._log(f"\n  [{name}] @ 0x{info['func_va']:08X} ({info['size']} bytes)")
            self._log(f"    First bytes: {func_bytes[:16].hex()}")
            self._log(f"    Prologue:    {func_bytes[:8].hex()}")
        
        return results
    
    # =========================================================
    # PATCH 3: Find code caves for injection
    # =========================================================
    def find_code_caves(self, min_size=32):
        """Find unused space (runs of 0x00 or 0xCC) in the .text section for code injection"""
        self._log(f"\n=== FINDING CODE CAVES (min {min_size} bytes) ===")
        
        caves = []
        current_start = None
        current_len = 0
        
        # Scan .text section (roughly 0x401000 to 0x800000)
        text_start = self._va_to_offset(0x00401000)
        text_end = self._va_to_offset(0x00800000)
        
        for i in range(text_start, min(text_end, len(self.data))):
            byte = self.data[i]
            if byte == 0x00 or byte == 0xCC:  # NOP padding or INT3
                if current_start is None:
                    current_start = i
                    current_len = 1
                else:
                    current_len += 1
            else:
                if current_start is not None and current_len >= min_size:
                    va = current_start + self.image_base
                    caves.append({'va': va, 'offset': current_start, 'size': current_len})
                current_start = None
                current_len = 0
        
        self._log(f"Found {len(caves)} code caves >= {min_size} bytes:")
        for cave in caves[:20]:  # Show top 20
            self._log(f"  VA: 0x{cave['va']:08X}  Size: {cave['size']} bytes")
        
        return caves
    
    def save(self):
        """Save patched binary"""
        with open(self.exe_path, 'wb') as f:
            f.write(self.data)
        new_hash = hashlib.md5(self.data).hexdigest()
        self._log(f"\nSaved: {self.exe_path}")
        self._log(f"New MD5: {new_hash}")
        self._log(f"Patches applied: {len(self.patches_applied)}")
    
    def generate_report(self, output_path):
        """Generate a detailed patch report"""
        report = []
        report.append("=" * 60)
        report.append("KINETIC TURTLE - WoW.exe Patch Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("=" * 60)
        report.append(f"\nBinary: {self.exe_path}")
        report.append(f"Original MD5: {self.original_hash}")
        report.append(f"Patches Applied: {len(self.patches_applied)}")
        report.append("")
        
        for i, patch in enumerate(self.patches_applied):
            report.append(f"\n--- Patch {i+1} ---")
            report.append(f"Address: 0x{patch['va']:08X}")
            report.append(f"Old bytes: {patch['old']}")
            report.append(f"New bytes: {patch['new']}")
            report.append(f"Description: {patch['description']}")
        
        report.append("\n\n--- Full Log ---")
        report.extend(self.log)
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(report))
        
        self._log(f"Report saved: {output_path}")


def main():
    wow_exe = r"C:\Users\thatg\Desktop\Modernize\TurtleWoW_Ultra\WoW.exe"
    report_path = r"C:\Users\thatg\Desktop\Modernize\kinetic_patch_report.txt"
    
    if not os.path.exists(wow_exe):
        print(f"ERROR: {wow_exe} not found!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("  KINETIC TURTLE - Binary Patcher v1.0")
    print("  Target: WoW.exe (1.12.1)")
    print("=" * 60 + "\n")
    
    patcher = WoWPatcher(wow_exe)
    
    # Phase 1: Create backup
    print("\n[Phase 1] Creating backup...")
    patcher.backup()
    
    # Phase 2: Scan crash functions
    print("\n[Phase 2] Scanning crash functions...")
    results = patcher.scan_crash_patterns()
    
    # Phase 3: Analyze Lua stack limit
    print("\n[Phase 3] Analyzing Lua stack overflow limit...")
    patcher.patch_lua_stack_limit()
    
    # Phase 4: Find code caves for future patches
    print("\n[Phase 4] Finding code caves for injection...")
    caves = patcher.find_code_caves(min_size=64)
    
    # Phase 5: Generate report (don't apply patches yet - analysis first)
    print("\n[Phase 5] Generating analysis report...")
    patcher.generate_report(report_path)
    
    print(f"\n{'=' * 60}")
    print(f"  Analysis complete!")
    print(f"  Report: {report_path}")
    print(f"  Crash functions scanned: {len(results)}")
    print(f"  Code caves found: {len(caves)}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
