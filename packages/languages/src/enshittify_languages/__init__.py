"""Language-aware repository inspection."""

from enshittify_languages.detect import (
    RepositoryInspection,
    inspect_repository,
    iter_python_files,
)

__all__ = ["RepositoryInspection", "inspect_repository", "iter_python_files"]
