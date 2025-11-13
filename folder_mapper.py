import os
import sys


def generate_tree(
    directory, output_file="folder_structure.txt", exclude_dirs=None, exclude_files=None
):
    """
    Generates a tree structure of the given directory, summarizing .png files
    instead of listing them individually.

    Args:
        directory (str): The directory to map.
        output_file (str): The name of the output file.
        exclude_dirs (list): A list of directory names to exclude.
        exclude_files (list): A list of file names to exclude.
    """
    if exclude_dirs is None:
        exclude_dirs = [".git", "__pycache__", ".vscode", "node_modules", ".idea"]
    if exclude_files is None:
        # Note: .png files are handled separately, not technically excluded.
        exclude_files = [".DS_Store", "Thumbs.db", ".gitignore"]

    tree_lines = []

    def build_tree(path, prefix=""):
        """Recursively builds the tree structure."""
        # Add the root directory name to the output
        if not prefix:
            tree_lines.append(f"{os.path.basename(os.path.abspath(path))}/")

        try:
            # Get all items in the current directory
            all_items = os.listdir(path)
        except PermissionError:
            tree_lines.append(f"{prefix}└── [Permission Denied]")
            return

        # Separate items into directories, png files, and other files
        dirs = []
        other_files = []
        png_count = 0

        for item in all_items:
            # Skip explicitly excluded directories and files
            if item in exclude_dirs or item in exclude_files:
                continue

            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                dirs.append(item)
            elif item.lower().endswith(".png"):
                png_count += 1
            else:
                other_files.append(item)

        # Sort directories and other files alphabetically for consistent output
        sorted_items = sorted(dirs) + sorted(other_files)

        # Process all directories and non-png files
        for i, item_name in enumerate(sorted_items):
            is_last = (i == len(sorted_items) - 1) and (png_count == 0)
            connector = "└── " if is_last else "├── "
            tree_lines.append(f"{prefix}{connector}{item_name}")

            item_path = os.path.join(path, item_name)
            if os.path.isdir(item_path):
                extension = "    " if is_last else "│   "
                build_tree(item_path, prefix + extension)

        # Add the PNG summary line at the end for this directory, if needed
        if png_count > 0:
            connector = "└── "
            tree_lines.append(f"{prefix}{connector}Number of pngs: ({png_count})")

    # Start building the tree from the specified directory
    build_tree(directory)

    # Write the generated tree to the output file
    with open(output_file, "w", encoding="utf-8") as f:
        for line in tree_lines:
            f.write(line + "\n")

    return tree_lines


def main():
    """Main execution function."""
    # Use the directory from command-line argument or default to current directory
    if len(sys.argv) > 1:
        directory = sys.argv[1]
        if not os.path.isdir(directory):
            print(f"Error: Directory '{directory}' does not exist.")
            return
    else:
        directory = os.getcwd()

    # Create a descriptive output filename
    dir_name = os.path.basename(os.path.abspath(directory))
    output_file = f"{dir_name}_structure.txt"

    print(f"Mapping folder structure for: {directory}")
    print(f"Output will be saved to: {output_file}")

    try:
        # Generate the tree and get the lines for printing
        tree_lines = generate_tree(directory, output_file)

        # Print the final structure to the console
        print("\n--- Folder Structure ---")
        for line in tree_lines:
            print(line)
        print("------------------------")
        print(f"\nSuccessfully saved folder map to {output_file}")

    except Exception as e:
        print(f"An error occurred while generating the tree: {e}")


if __name__ == "__main__":
    main()
