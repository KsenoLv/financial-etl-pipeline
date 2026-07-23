## Payment Provider Configuration

Pipeline supports multiple payment providers, each with its own report format, field names and normalization rules.

To keep this public repository simple while showing the overall design, only four example payment provider configurations are included:

- Aifory
- Biso
- Jeton
- Tunzer

These examples show how different provider formats are converted into one common financial transaction structure, including column mapping, default values, date formats, transaction IDs, and transformation rules.
The production system supports additional providers using the same configuration-driven approach.

## Configuration Variants

This repository demonstrates two valid approaches for organizing provider configurations.

### 1. Modular configuration

Each provider is stored in its own module.

```text
processors/
├── aifory.py
├── biso.py
├── jeton.py
└── tunzer.py
```

This approach scales well as the number of supported providers grows.

Advantages:

- Easier maintenance
- Better code organization
- Independent provider updates
- Cleaner Git history
- Simple addition of new providers

### 2. Single-file configuration

For smaller projects, all provider mappings can also be stored in a single configuration file.

```text
processors_config_single_file.py
```

This approach keeps everything in one place and may be preferable for projects with only a small number of payment providers.
Both implementations contain the same mapping logic and produce identical results. The modular approach is used throughout this repository because it provides better maintainability for larger ETL systems.