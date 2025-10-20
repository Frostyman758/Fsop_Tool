FOX Engine FSOP Packer/Unpacker
By Blue :)
A command-line tool to pack and unpack .fsop files used in the FOX Engine.

Usage

Auto Mode:
python fsop_tool.py <file.fsop or folder>
	•	If .fsop file: unpacks it
	•	If folder: packs it back to .fsop

Manual Mode:
python fsop_tool.py unpack <input.fsop> [output_dir]
python fsop_tool.py pack <input_dir> [output.fsop]

Workflow Example:
	1.	Unpack an FSOP file:
python fsop_tool.py shader.fsop
Creates shader_unpacked/
	2.	Edit or add new .fxc files in the unpacked folder.
	3.	Repack:
python fsop_tool.py shader_unpacked
Creates shader.fsop

Adding a New Shader:

Edit metadata.json and add an entry like:
{name: “MyShader”, vertex_shader_file: “MyShader_vs.fxc”, pixel_shader_file: “MyShader_ps.fxc”}

Optional field:
“encoding”: “shift-jis” or “utf-8” (default is auto-detect)
