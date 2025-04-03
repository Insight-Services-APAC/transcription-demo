import ast
import os

EXCLUDE_DIRS = {"venv", ".venv", "__pycache__", "env", "build", "dist", "site-packages"}


class JsonifyRemover(ast.NodeTransformer):

    def visit_Assign(self, node):
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and (node.value.func.id == "jsonify")
            and (len(node.value.args) == 1)
            and isinstance(node.value.args[0], (ast.Dict, ast.Call))
        ):
            node.value = node.value.args[0]
        return node


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = ast.parse(source)
        new_tree = JsonifyRemover().visit(tree)
        ast.fix_missing_locations(new_tree)
        new_source = ast.unparse(new_tree)
        if source != new_source:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_source)
            print(f"✔ Updated: {filepath}")
    except Exception as e:
        print(f"⚠️ Skipped {filepath} due to error: {e}")


def walk_py_files(root_dir):
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith(".py"):
                yield os.path.join(root, file)


if __name__ == "__main__":
    project_root = os.getcwd()
    print(f"Processing Python files in: {project_root}")
    count = 0
    for file_path in walk_py_files(project_root):
        process_file(file_path)
        count += 1
    print(f"Finished processing {count} Python files")
