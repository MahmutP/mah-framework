# Prompts for Fixing Project Flaws

Here is a list of prompts you can use (one by one) to fix the issues identified in `project_analysis_report.md`.

## 1. Refactor SharedState & Dependency Injection
**Goal:** Reduce reliance on the global `SharedState` singleton and introduce proper dependency injection.

> **Prompt:**
> "I want to refactor the project to reduce the reliance on the global `SharedState` singleton.
>
> Please allow `CommandManager` and `ModuleManager` to store their own data (commands and modules) instead of relying on `shared_state`.
> Then, modify the `Console` class and `main.py` to pass these manager instances directly to the components that need them (dependency injection).
> Finally, remove the global `shared_state` import where it is no longer needed, making the architecture more modular and testable."

## 2. Modernize Path Handling with Pathlib
**Goal:** Replace fragile string manipulation for file paths with the robust `pathlib` library.

> **Prompt:**
> "I want to modernize the file path handling in the `core` module.
>
> Please replace all usages of `os.path` and manual string manipulation (like `[:-3]` or `replace`) with Python's `pathlib` library.
> Specifically, update `CommandManager.load_commands` and `ModuleManager.load_modules` to use `Path` objects for finding files, extracting stems (filenames without extensions), and managing directory paths. This will make the code more robust across different operating systems."

## 3. Improve Error Handling
**Goal:** Replace broad `except Exception` blocks with specific error handling and ensure proper logging.

> **Prompt:**
> "I want to improve the error handling in `CommandManager` and `ModuleManager`.
>
> Currently, there are broad `try...except Exception` blocks that swallow specific errors. Please refactor this to:
> 1. Catch specific exceptions like `ImportError`, `SyntaxError`, and `FileNotFoundError` individually where appropriate.
> 2. Log these errors with `logger.exception()` to capture the full traceback in the logs.
> 3. Provide clear, user-friendly error messages to the console without showing raw stack traces unless necessary."

## 4. Separate Console Logic
**Goal:** Decouple the UI logic from the business logic in `core/console.py`.

> **Prompt:**
> "I want to refactor `core/console.py` to separate concerns better.
>
> Currently, the `Console` class handles both the UI (prompt_toolkit session) and the logic for executing commands.
> Please extract the command execution logic into a cleaner interface or helper method, keeping the `Console` class strictly focused on the User Interface (rendering the prompt, handling input, printing outputs). Ensure that `CommandManager` is responsible for the 'how' of execution, while `Console` is just responsible for the 'when'."
