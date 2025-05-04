# Obsidian PDF Multi Export

[![PyPI version](https://badge.fury.io/py/obsidian-pdf-multi-export.svg)](https://badge.fury.io/py/obsidian-pdf-multi-export)
<!-- Add other badges as needed: build status, coverage, license -->

A command-line tool to synchronize directories, specifically designed for Obsidian vaults, converting Markdown files to PDF using Pandoc or Typst while preserving the directory structure and copying other file types.

## Problem Solved

Obsidian is a fantastic tool for note-taking and personal knowledge management using Markdown files. However, sharing notes or entire vaults with non-technical users can be challenging, as Markdown isn't universally readable like PDF. This tool bridges that gap by allowing you to maintain your notes in Obsidian and easily export a shareable PDF version of your vault (or specific folders within it).

It handles:

- Converting `.md` files to `.pdf` using either Pandoc or Typst (configurable).
- Copying all other file types (images, attachments, etc.) as-is.
- Maintaining the original directory structure in the output folder.
- Configurable converter commands (Pandoc/Typst) for customization (e.g., using specific templates, fonts, or engines).
- Managing multiple input/output directory mappings.

## Installation

```bash
uv tool install git+https://github.com/KoStard/obsidian_pdf_multi_export
```

Ensure you have [Pandoc](https://pandoc.org/installing.html) installed and accessible in your system's PATH, or configure the path using the tool.

## Usage

The tool uses a command-line interface.

```bash
obsidian-pdf-multi-export --help
```

### Configuration

Configuration is stored in `~/.config/obsidian_pdf_multi_export/config.ini`. You can manage it using the `config` commands or by editing the file directly.

**1. Add Directory Mappings:**

Tell the tool which input directories (your Obsidian folders) should be synchronized to which output directories.

```bash
# Example: Map vault's 'Project A' folder to a 'Project A PDF Export' folder
obsidian-pdf-multi-export config add "/path/to/your/obsidian/vault/Project A" "/path/to/your/exports/Project A PDF Export"

# Add more mappings as needed
obsidian-pdf-multi-export config add "/path/to/another/vault/Notes" "/path/to/your/exports/Notes PDF"
```

**2. (Optional) Configure Pandoc:**

By default, the tool calls `pandoc`. If your Pandoc executable is in a non-standard location or you need custom arguments:

```bash
# Set a specific pandoc path
obsidian-pdf-multi-export config set-pandoc --path /opt/pandoc/bin/pandoc

# Set custom arguments (e.g., use a specific template)
# Note: Provide arguments as a single string
obsidian-pdf-multi-export config set-pandoc --args "--template=mytemplate.latex --pdf-engine=xelatex"

# Set both path and arguments
obsidian-pdf-multi-export config set-pandoc --path /opt/pandoc/bin/pandoc --args "--variable=fontsize:12pt"
```

The tool automatically adds the `-i input.md -o output.pdf` arguments during conversion.

**3. List Configuration:**

Check your current setup:

```bash
obsidian-pdf-multi-export config list
```

**4. Remove Mappings:**

```bash
obsidian-pdf-multi-export config remove "/path/to/your/obsidian/vault/Project A"
```

### Synchronization

Once configured, run the synchronization process:

```bash
obsidian-pdf-multi-export sync
```

This will:

1. Iterate through all configured input/output mappings.
2. For each mapping:
    - Clean the corresponding output directory (prompting for deletion of files not present in the source).
    - Recursively scan the input directory.
    - Copy non-Markdown files to the output directory, preserving structure.
    - Convert Markdown files (`.md`) to PDF (`.pdf`) using the configured Pandoc command and save them in the corresponding location in the output directory.

## How it Works (Internals)

1. **Configuration Loading:** Reads mappings and Pandoc settings from `config.ini`.
2. **Directory Traversal:** Walks through each configured input directory.
3. **File Handling:**
    - **Markdown (`.md`):** Constructs and executes a Pandoc command like `pandoc [configured args] -i <input.md> -o <output.pdf>`.
    - **Other Files:** Copies the file directly using `shutil.copy2` (preserving metadata).
4. **Output Directory Management:** Creates necessary subdirectories in the output path. Handles cleanup of stale files (files in the output directory that no longer exist in the input directory) by prompting the user.

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` (to be created) file for guidelines.

## License

This project is licensed under the MIT License - see the `LICENSE` (to be created) file for details.
