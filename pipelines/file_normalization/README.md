# File Normalization Pipeline

The repository demonstrates two approaches for normalizing payment provider
reports into a unified transaction format.

Both implementations produce the same normalized output while using different
architectural designs.

---

## Project Structure

```text
file_normalization/
│
├── modular/
│   ├── new_map.py
│   └── README.md
│
└── standalone/
    ├── aifory.py
    ├── biso.py
    ├── jeton.py
    ├── tunzer.py
    └── README.md
```

Configuration files are stored separately:

```text
config/
│
├── processors_config.py
├── processors_config_single_file.py
└── processors/
    ├── aifory.py
    ├── biso.py
    ├── jeton.py
    └── tunzer.py
```

---

# Architecture 1 — Modular Pipeline (Recommended)

The **Modular Pipeline** demonstrates a scalable architecture designed for
projects supporting many payment providers.

A single normalization engine loads provider-specific mappings from dedicated
configuration modules.

```
new_map.py
      │
      ▼
processors_config.py
      │
      ▼
processors/
    ├── aifory.py
    ├── biso.py
    ├── jeton.py
    └── tunzer.py
```

### Advantages

- Single normalization engine
- Easy to maintain
- Simple to extend
- Provider logic isolated into individual modules
- Suitable for large ETL projects

---

# Architecture 2 — Standalone Pipeline

The **Standalone Pipeline** demonstrates a simpler architecture where every
payment provider has its own executable normalization script.

Each script loads its mapping from a shared configuration file.

```
aifory.py
biso.py
jeton.py
tunzer.py
      │
      ▼
processors_config_single_file.py
```

### Advantages

- Easy to understand
- Minimal abstraction
- Convenient for small projects
- Simple to debug

---

# Configuration

The repository contains two configuration styles.

### Modular configuration

```
config/
├── processors_config.py
└── processors/
```

Each provider is stored in its own configuration module.

### Single-file configuration

```
config/
└── processors_config_single_file.py
```

All provider mappings are stored in a single configuration file.

---

# Included Providers

To keep the public repository concise, only four representative payment
providers are included:

- Aifory
- Biso
- Jeton
- Tunzer

The production system supports additional providers using the same
configuration-driven principles demonstrated in this repository.