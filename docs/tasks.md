# Task 1 - Implement MLP of the project (Completed)

## Requirements

Build a CLI tool `obsidian_pdf_multi_export` that given a folder, replicates it in the target directory (if the directory exists, cleans it up first), while copying all the non-markdown files as is, while for markdowns, runs a pandoc command to generate PDF.

The program should be self-sufficient and flexible through a ~/.config/obsidian_pdf_multi_export/config.ini file.

- The pandoc command should be adjustable here. The `-i input_file.md -o output_path.pdf` will be added by the program, but the config can change the path of pandoc and provide additional arguments like this: `pandoc --custom commands --etc`, so it becomes `pandoc --custom commands --etc -i input_file.md -o output_path.pdf`
- The input path to output path dictionary is configured in the config file as well.

In the MLP, all files should be copied and rendered from scratch. Overwrite the existing files in the target directory when the names match. But if there are files in target directory that are no longer present in the source directory, ask one by one to the user (with option to choose "All" or "Skip All" as well) to delete or skip the files.

The application provides an intuitive interface both to run the sync, and to configure it. While the user can also open the config file in editor and manually configure it, we should also provide nice CLI commands to add/remove input/output path pairs.

All input/output directory pairs are executed when the application runs.

The interface uses emojis and intuitively shows the progress.

README is well formatted for an open source project. It will be published to GitHub under user KoStard/. Name of the repo will be obsidian_pdf_multi_export.
The README should explain the problem it's solving, how to configure it, how it works, etc.

Why I personally need this tool: I work on a project in Obsidian, there are some attachments (pdfs, images, etc), that themselves are valuable as well. I also have a number of markdown pages in Obsidian. These markdown pages is where the problem is. I want to share the project files with family and friends, but Markdown is not very easy format for non-tech audience to read. Instead, PDF is excellent option. Hence we'll use it. This is my personal use case, there might be others, so don't index on it in README.

# Task 2 - Add Typst as an alternative converter (Completed)

## Requirements
- Allow users to choose between Pandoc and Typst for Markdown-to-PDF conversion via a CLI option during sync (`--converter`).
- Add configuration options for Typst (executable path, arguments) similar to Pandoc in `config.ini`.
- Implement CLI commands (`config set-typst`, update `config list`) to manage Typst configuration.
- Update the synchronizer logic to use the selected converter and its configuration.
- Ensure appropriate error handling if the selected converter is not found or fails.

# Future tasks
- When the command is executed, it checks which files have changed since the last execution and runs the commands only for them, to save time. # TODO: Task 3
