#!/usr/bin/env python3
"""
MGSV TPP Graphics Debugger Patcher

This script patches mgsvtpp.exe to allow graphics debuggers (RenderDoc) and 
mod packages (ReShade) to work by bypassing the CheckModuleHook function.

Based on: https://mgsvmoddingwiki.github.io/Attaching_graphics_debuggers/
"""

import sys
import os
import shutil
from pathlib import Path


def patch_mgsv_exe(exe_path):
    """
    Patches mgsvtpp.exe to bypass graphics debugger checks.
    
    Args:
        exe_path: Path to mgsvtpp.exe
    """
    # File offset and expected bytes
    FILE_OFFSET = 0x2ba642
    EXPECTED_BYTES = bytes([0x0F, 0x84, 0x1F, 0x04, 0x00, 0x00])  # JZ LAB_1402bb667
    PATCH_BYTES = bytes([0x48, 0xE9, 0x00, 0x00, 0x00, 0x00])     # JMP LAB_1402bb248
    
    exe_path = Path(exe_path)
    
    # Validate file exists
    if not exe_path.exists():
        print(f"Error: File not found: {exe_path}")
        return False
    
    # Create backup
    backup_path = exe_path.with_suffix('.exe.bak')
    if not backup_path.exists():
        print(f"Creating backup: {backup_path}")
        shutil.copy2(exe_path, backup_path)
    else:
        print(f"Backup already exists: {backup_path}")
    
    # Read the file
    print(f"Reading {exe_path}...")
    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())
    
    # Verify expected bytes at offset
    actual_bytes = data[FILE_OFFSET:FILE_OFFSET + 6]
    
    if actual_bytes == EXPECTED_BYTES:
        print(f"Found expected bytes at offset 0x{FILE_OFFSET:X}")
        print(f"  Original: {' '.join(f'{b:02X}' for b in actual_bytes)}")
        
        # Apply patch
        data[FILE_OFFSET:FILE_OFFSET + 6] = PATCH_BYTES
        print(f"  Patched:  {' '.join(f'{b:02X}' for b in PATCH_BYTES)}")
        
        # Write patched file
        with open(exe_path, 'wb') as f:
            f.write(data)
        
        print("\n✓ Patch applied successfully!")
        print(f"✓ Graphics debuggers (RenderDoc) and mod packages (ReShade) should now work.")
        return True
        
    elif actual_bytes == PATCH_BYTES:
        print(f"File is already patched!")
        print(f"  Current bytes at 0x{FILE_OFFSET:X}: {' '.join(f'{b:02X}' for b in actual_bytes)}")
        return True
        
    else:
        print(f"Error: Unexpected bytes at offset 0x{FILE_OFFSET:X}")
        print(f"  Expected: {' '.join(f'{b:02X}' for b in EXPECTED_BYTES)}")
        print(f"  Found:    {' '.join(f'{b:02X}' for b in actual_bytes)}")
        print(f"\nThis may be a different version of mgsvtpp.exe")
        print(f"The patch may not be compatible with this version.")
        return False


def restore_backup(exe_path):
    """Restores the original exe from backup."""
    exe_path = Path(exe_path)
    backup_path = exe_path.with_suffix('.exe.bak')
    
    if not backup_path.exists():
        print(f"Error: Backup file not found: {backup_path}")
        return False
    
    print(f"Restoring from backup: {backup_path}")
    shutil.copy2(backup_path, exe_path)
    print("✓ Original file restored successfully!")
    return True


def main():
    print("=" * 60)
    print("MGSV TPP Graphics Debugger Patcher")
    print("=" * 60)
    print()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} <path_to_mgsvtpp.exe>")
        print(f"  {sys.argv[0]} <path_to_mgsvtpp.exe> --restore")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} mgsvtpp.exe")
        print(f"  {sys.argv[0]} \"C:\\Program Files\\Steam\\steamapps\\common\\MGS_TPP\\mgsvtpp.exe\"")
        print(f"  {sys.argv[0]} mgsvtpp.exe --restore")
        sys.exit(1)
    
    exe_path = sys.argv[1]
    
    # Check for restore flag
    if len(sys.argv) > 2 and sys.argv[2] == '--restore':
        restore_backup(exe_path)
    else:
        patch_mgsv_exe(exe_path)


if __name__ == "__main__":
    main()
