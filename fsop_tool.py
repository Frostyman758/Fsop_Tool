#!/usr/bin/env python3
"""
FOX Engine FSOP Packer/Unpacker
Handles Konami FOX Engine shader operation files (.fsop)
"""

import struct
import sys
import os
from pathlib import Path
import json


class FSOPUnpacker:
    """Unpacks FSOP files into individual shader files and metadata"""
    
    def __init__(self, fsop_path):
        self.fsop_path = Path(fsop_path)
        self.shaders = []
    
    @staticmethod
    def xor_decrypt(data):
        """Decrypt data using XOR 0x9C"""
        return bytes(b ^ 0x9C for b in data)
    
    @staticmethod
    def sanitize_filename(name):
        """Remove invalid filename characters"""
        # Remove null bytes and other problematic characters
        name = name.replace('\x00', '').strip()
        # Replace invalid Windows filename characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        # Ensure name is not empty
        if not name:
            name = "unnamed"
        return name
    
    def unpack(self, output_dir=None):
        """Unpack FSOP file to directory"""
        if output_dir is None:
            output_dir = self.fsop_path.stem + "_unpacked"
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        with open(self.fsop_path, 'rb') as f:
            data = f.read()
        
        offset = 0
        shader_index = 0
        
        while offset < len(data):
            # Read name length
            name_length = data[offset]
            offset += 1
            
            # Read name (try multiple encodings)
            name_bytes = data[offset:offset + name_length]
            try:
                # Try Shift-JIS first (common for Japanese games)
                name_raw = name_bytes.decode('shift-jis')
            except:
                try:
                    # Fall back to UTF-8
                    name_raw = name_bytes.decode('utf-8')
                except:
                    # Last resort: Latin-1 (never fails)
                    name_raw = name_bytes.decode('latin-1')
            
            name = self.sanitize_filename(name_raw)
            
            # Determine encoding used
            encoding = 'shift-jis'
            try:
                name_raw.encode('shift-jis')
            except:
                try:
                    name_raw.encode('utf-8')
                    encoding = 'utf-8'
                except:
                    encoding = 'latin-1'
            
            offset += name_length
            
            # Read vertex shader size
            vs_size = struct.unpack('<I', data[offset:offset + 4])[0]
            offset += 4
            
            # Read vertex shader data (XOR encrypted)
            vs_data_encrypted = data[offset:offset + vs_size]
            vs_data = self.xor_decrypt(vs_data_encrypted)
            offset += vs_size
            
            # Read pixel shader size
            ps_size = struct.unpack('<I', data[offset:offset + 4])[0]
            offset += 4
            
            # Read pixel shader data (XOR encrypted)
            ps_data_encrypted = data[offset:offset + ps_size]
            ps_data = self.xor_decrypt(ps_data_encrypted)
            offset += ps_size
            
            # Store shader info - minimal metadata
            shader_info = {
                'name': name_raw,
                'encoding': encoding,
                'vertex_shader_file': f"{name}_vs.fxc",
                'pixel_shader_file': f"{name}_ps.fxc"
            }
            self.shaders.append(shader_info)
            
            # Write vertex shader (no numbering)
            vs_file = output_path / f"{name}_vs.fxc"
            with open(vs_file, 'wb') as f:
                f.write(vs_data)
            
            # Write pixel shader (no numbering)
            ps_file = output_path / f"{name}_ps.fxc"
            with open(ps_file, 'wb') as f:
                f.write(ps_data)
            
            print(f"Extracted shader {shader_index}: {name_raw}")
            print(f"  -> {name}_vs.fxc ({vs_size} bytes)")
            print(f"  -> {name}_ps.fxc ({ps_size} bytes)")
            
            shader_index += 1
        
        # Write metadata - clean and minimal
        metadata_file = output_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'shaders': self.shaders,
                '_info': 'Edit .fxc files freely. To add a shader: add entry with "name", "vertex_shader_file", "pixel_shader_file". Order matters for repacking.'
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Unpacked {len(self.shaders)} shaders to {output_path}")
        print(f"✓ Metadata saved - preserves shader order and original names")
        return output_path


class FSOPPacker:
    """Packs shader files back into FSOP format"""
    
    def __init__(self, input_dir):
        self.input_dir = Path(input_dir)
        self.metadata_file = self.input_dir / "metadata.json"
    
    @staticmethod
    def xor_encrypt(data):
        """Encrypt data using XOR 0x9C"""
        return bytes(b ^ 0x9C for b in data)
    
    @staticmethod
    def sanitize_name(name):
        """Sanitize name for filename"""
        name = name.replace('\x00', '').strip()
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        if not name:
            name = "unnamed"
        return name
    
    @staticmethod
    def detect_encoding(text):
        """Detect the most compact encoding for a text string"""
        # Try encodings in order of preference
        # ASCII is subset of both shift-jis and utf-8, so try smallest first
        
        # Check if pure ASCII (most common for shader names)
        try:
            text.encode('ascii')
            return 'ascii'  # ASCII works with both shift-jis and utf-8
        except:
            pass
        
        # Try shift-jis (common for Japanese text)
        try:
            encoded_sjis = text.encode('shift-jis')
            # Also check if it can be decoded back correctly
            if text == encoded_sjis.decode('shift-jis'):
                # Try utf-8 to see which is smaller
                try:
                    encoded_utf8 = text.encode('utf-8')
                    if len(encoded_utf8) <= len(encoded_sjis):
                        return 'utf-8'
                except:
                    pass
                return 'shift-jis'
        except:
            pass
        
        # Try UTF-8
        try:
            text.encode('utf-8')
            return 'utf-8'
        except:
            pass
        
        # Last resort
        return 'latin-1'
    
    def pack(self, output_file=None):
        """Pack shader files into FSOP"""
        if output_file is None:
            output_file = self.input_dir.stem.replace('_unpacked', '') + '.fsop'
        
        # Load metadata
        if not self.metadata_file.exists():
            print("Error: metadata.json not found in input directory")
            print("The metadata.json file is required to maintain shader order and names.")
            return None
        
        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Find all .fxc files in directory
        all_fxc_files = set()
        for fxc_file in self.input_dir.glob("*.fxc"):
            all_fxc_files.add(fxc_file.name)
        
        # Track which files are already in metadata
        known_files = set()
        for shader_info in metadata['shaders']:
            if 'vertex_shader_file' in shader_info:
                known_files.add(shader_info['vertex_shader_file'])
            if 'pixel_shader_file' in shader_info:
                known_files.add(shader_info['pixel_shader_file'])
        
        # Find new shader pairs
        new_shaders = []
        processed_files = set()
        
        for fxc_file in all_fxc_files:
            if fxc_file in known_files or fxc_file in processed_files:
                continue
            
            # Check if this is a vertex shader with matching pixel shader
            if fxc_file.endswith('_vs.fxc'):
                base_name = fxc_file[:-7]  # Remove '_vs.fxc'
                ps_file = f"{base_name}_ps.fxc"
                
                if ps_file in all_fxc_files and ps_file not in known_files:
                    # Detect best encoding for the shader name
                    encoding = self.detect_encoding(base_name)
                    
                    # Add null terminator if not present
                    shader_name = base_name if base_name.endswith('\x00') else base_name + '\x00'
                    
                    new_shaders.append({
                        'name': shader_name,
                        'encoding': encoding,
                        'vertex_shader_file': fxc_file,
                        'pixel_shader_file': ps_file
                    })
                    processed_files.add(fxc_file)
                    processed_files.add(ps_file)
                    print(f"Found new shader: {base_name} (encoding: {encoding})")
        
        # Add new shaders to metadata and save if any were found
        if new_shaders:
            metadata['shaders'].extend(new_shaders)
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"✓ Added {len(new_shaders)} new shader(s) to metadata.json\n")
        
        output_data = bytearray()
        packed_count = 0
        
        # Process shaders in metadata order
        for i, shader_info in enumerate(metadata['shaders']):
            # Get shader name - required field
            if 'name' not in shader_info:
                print(f"Error: Shader entry {i} missing 'name' field, skipping")
                continue
            
            shader_name = shader_info['name']
            
            # Ensure null terminator is present
            if not shader_name.endswith('\x00'):
                shader_name += '\x00'
            
            # Get filenames - required fields
            if 'vertex_shader_file' not in shader_info or 'pixel_shader_file' not in shader_info:
                print(f"Error: Shader '{shader_name}' missing file fields, skipping")
                continue
                
            vs_filename = shader_info['vertex_shader_file']
            ps_filename = shader_info['pixel_shader_file']
            
            vs_file = self.input_dir / vs_filename
            ps_file = self.input_dir / ps_filename
            
            if not vs_file.exists() or not ps_file.exists():
                print(f"Warning: Shader files '{vs_filename}' or '{ps_filename}' not found, skipping")
                continue
            
            # Read shader data
            with open(vs_file, 'rb') as f:
                vs_data = f.read()
            
            with open(ps_file, 'rb') as f:
                ps_data = f.read()
            
            # Encode shader name using stored encoding
            encoding = shader_info.get('encoding', 'shift-jis')
            try:
                name_bytes = shader_name.encode(encoding)
            except:
                # Fallback encoding chain
                try:
                    name_bytes = shader_name.encode('shift-jis')
                except:
                    try:
                        name_bytes = shader_name.encode('utf-8')
                    except:
                        name_bytes = shader_name.encode('latin-1')
            
            # Encrypt shader data with XOR 0x9C
            vs_data_encrypted = self.xor_encrypt(vs_data)
            ps_data_encrypted = self.xor_encrypt(ps_data)
            
            # Write name length and name bytes
            output_data.append(len(name_bytes))
            output_data.extend(name_bytes)
            
            # Write vertex shader size and encrypted data
            output_data.extend(struct.pack('<I', len(vs_data_encrypted)))
            output_data.extend(vs_data_encrypted)
            
            # Write pixel shader size and encrypted data
            output_data.extend(struct.pack('<I', len(ps_data_encrypted)))
            output_data.extend(ps_data_encrypted)
            
            print(f"Packed shader {i}: {shader_name}")
            print(f"  VS: {len(vs_data)} bytes, PS: {len(ps_data)} bytes")
            packed_count += 1
        
        # Write output file
        with open(output_file, 'wb') as f:
            f.write(output_data)
        
        print(f"\n✓ Packed {packed_count} shaders to {output_file}")
        return output_file


def main():
    if len(sys.argv) < 2:
        print("FOX Engine FSOP Packer/Unpacker")
        print("\nUsage:")
        print("  Auto mode:  python fsop_tool.py <file.fsop or folder>")
        print("              - If .fsop file: unpacks it")
        print("              - If folder: packs it back to .fsop")
        print("  Manual:     python fsop_tool.py unpack <input.fsop> [output_dir]")
        print("  Manual:     python fsop_tool.py pack <input_dir> [output.fsop]")
        print("\nWorkflow:")
        print("  1. python fsop_tool.py shader.fsop     # Unpacks to shader_unpacked/")
        print("  2. Edit .fxc files or add new ones")
        print("  3. python fsop_tool.py shader_unpacked # Repacks to shader.fsop")
        print("\nTo add a new shader to metadata.json:")
        print('  {"name": "MyShader", "vertex_shader_file": "MyShader_vs.fxc", "pixel_shader_file": "MyShader_ps.fxc"}')
        print('  Optional: "encoding": "shift-jis" or "utf-8" (defaults to auto-detect)')
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    
    # Auto-detect mode: single argument that's a file or directory
    if len(sys.argv) == 2:
        if input_path.is_file() and input_path.suffix.lower() == '.fsop':
            # Unpack mode
            print(f"Auto-detecting: Unpacking {input_path.name}...")
            unpacker = FSOPUnpacker(input_path)
            unpacker.unpack()
        elif input_path.is_dir():
            # Pack mode - detect output filename
            print(f"Auto-detecting: Packing {input_path.name}...")
            
            # Determine output filename
            if input_path.name.endswith('_unpacked'):
                output_file = input_path.name[:-9] + '.fsop'
            else:
                output_file = input_path.name + '.fsop'
            
            packer = FSOPPacker(input_path)
            packer.pack(output_file)
        else:
            print(f"Error: '{input_path}' is not a valid .fsop file or directory")
            sys.exit(1)
        return
    
    # Manual mode with explicit command
    command = sys.argv[1].lower()
    input_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    if command == 'unpack':
        unpacker = FSOPUnpacker(input_path)
        unpacker.unpack(output_path)
    
    elif command == 'pack':
        packer = FSOPPacker(input_path)
        packer.pack(output_path)
    
    else:
        print(f"Unknown command: {command}")
        print("Use 'unpack' or 'pack'")
        sys.exit(1)


if __name__ == '__main__':
    main()
