# ADSynth Experiment Interface

This README explains the modifications made to ADSynth to support percolation, prediction, and mitigation experiments.

The project supports five main operating modes:

1. **Dataset generation in UI**
2. **Dataset generation in CLI**
3. **Misconfiguration injection through the UI without mitigation**
4. **Misconfiguration injection through the UI with mitigation**
5. **Prediction through the CLI**

---

## Features

- Generate synthetic Active Directory graphs from ADSynth JSON parameter files as stated in project [README.md](../README.md).

- Run session, individual-permission, group-permission, and group-nesting injections.
- Execute injections as isolated, mixed, or sequential schedules.
- Enable online mitigation during injection experiments.
- Export experiment metrics to CSV and DuckDB.
- Train and evaluate 15 logistic-regression feature combinations from experiment CSV files.
- Calculate ROC-AUC, PR-AUC, precision, recall, F1, accuracy, detection rate, lead time, and confusion-matrix counts and store in DB.

---

## Project Workflow

```text
ADSynth JSON configuration
          |
          v
Generate baseline AD graph
          |
          v
Populate node tiers and caches
          |
          v
Inject misconfigurations
  |          |          |
isolated    mixed     sequence
          |
          v
Optional online mitigation
          |
          v
CSV + DuckDB experiment metrics
          |
          v
CLI prediction model suite
```

---

## Requirements

### Software

- Python 3.10 or later
- Neo4j
- Neo4j APOC plugin when JSON import is used
- Tkinter
- DuckDB
Optional
- Superset

### Python packages

Install the required packages in a virtual environment from project directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Tkinter is normally bundled with Python. On Linux, it may need to be installed separately:

```bash
sudo apt-get install python3-tk
```

---

## Recommended Project Structure

```text
ADSynth/
├── percolation_experiment_docs/
│   ├── README.md
├── adsynth/
│   ├── ADSynth.py
│   ├── experiment_params/
│   │   ├── vul_1k.json
│   │   ├── secure_1k.json
│   │   └── ...
│   └── utils/
├── ui/
│   ├── ADSynthUI.py
│   └── MisconfigInjectionPanel.py
├── analysis/
│   ├── csv/
│   └── plots/
├── generated_datasets/
├── requirements.txt
└── README.md
```

Modify commands as per your project structure.

---

## Neo4j Setup

Start Neo4j before opening the UI or CLI.

Default values used by the application are typically:

```text
URL:      bolt://localhost:7687
Username: neo4j
Domain:   TESTLAB.LOCALE
```

Enter the actual database password in the UI.



For JSON import, install and enable APOC. The application may use an import operation similar to:

```cypher
CALL apoc.import.json(...)
```

Ensure Neo4j is permitted to read the selected JSON path.

---
More information can be found on [Neo4j_guides](../Neo4J_guides.pdf)


## Superset and DuckDB Setup

Optionally, we can use Apache Superset for visualisation
Install Apache Superset following instructions given in the official repository and install in a virtual environment

[Apache Superset Documentation](https://github.com/apache/superset)

### Starting Superset
Activate the Superset virtual environment:

```
source venv/bin/activate

# Set the required environment variables:

export FLASK_APP=superset
export SUPERSET_SECRET_KEY="YOUR_SECRET_KEY"

superset run -p 8088 --with-threads --reload --debugger
```

1. Open Superset in a browser:

    http://localhost:8088

2. Install the DuckDB SQLAlchemy driver inside the same virtual environment used by Superset after starting superset

```
source venv/bin/activate
pip install duckdb duckdb-engine
```

In Superset:

1. Go to Settings → Data: Database Connections.
2. Select '+ Database'.
3. Choose DuckDB in supported databases.
4. Connect using SQLAlchemy URI:

```
# Sample SQLAlchemy URI for local file
duckdb:////Users/yagzanmanjunaath/adsynth_metrics.duckdb
```
5. Test the connection and Connect
6. Make sure the same DB file is pointed in the code.

---
# Mode 1: Dataset Generation in UI

Dataset generation creates a synthetic Active Directory graph from an ADSynth parameter JSON file and writes the generated graph to Neo4j.

## Start the UI

From the repository root:

```bash
cd <YOUR_PATH>/ADSynthMisconfig
PYTHONPATH=. python ui/ADSynthUI.py
```


## UI fields

| Field | Description |
|---|---|
| JSON Config | ADSynth parameter file used to create the graph |
| Security Level | `Customized`, `Low`, or `High` |
| Domain | Active Directory domain name |
| Neo4j URL | Neo4j Bolt connection URL |
| Neo4j Username | Neo4j username |
| Neo4j Password | Neo4j password |
| Random seed | Seed used for reproducible graph generation |
| Enable initial misconfiguration | Generates the baseline graph with configured initial misconfigurations |

## Procedure

1. Select a graph configuration, such as `vul_1k.json` or `secure_1k.json`.
2. Select the security level.
3. Enter the Neo4j connection details.
4. Set the domain and random seed.
5. Enable or disable initial misconfigurations.
6. Select **Test DB Connection**.
7. Select **Generate Graph**.
8. Wait for `Graph generation completed` in the output log.

After generation, the misconfiguration injection panel becomes visible.

## Reproducibility

Use the same:

- configuration JSON,
- security level,
- domain,
- random seed,
- initial-misconfiguration setting,

to reproduce the same randomized generation conditions.

---
# Mode 2: Automated Data Collection Using CLI

The automated data-collection workflow generates multiple synthetic Active Directory graphs and runs predefined misconfiguration-injection experiments across selected graph configurations, random seeds, initial graph variants, and injection schedules.

## Start the CLI

From the repository root:

```bash
cd <YOUR_PATH>/ADSynthMisconfig
PYTHONPATH=. python -m adsynth
```

At the ADSynth command prompt, run:

```text
collect_data
```

## Configuration fields

The automated workflow is controlled through the following configuration variables.

| Configuration               | Description                                                             |
| --------------------------- | ----------------------------------------------------------------------- |
| `DATA_COLLECTION_SEEDS`     | Random seeds used to generate reproducible graph realizations           |
| `DATA_COLLECTION_VARIANTS`  | Controls whether the generated graph includes initial misconfigurations |
| `DATA_COLLECTION_GRAPHS`    | Defines the graph names and JSON configuration paths                    |
| `DATA_COLLECTION_SCHEDULES` | Defines the misconfiguration types and their injection order            |
| `R`                         | Number of repeated realizations for each experiment                     |

Example:

```python
DATA_COLLECTION_SEEDS = [1, 2, 4, 8, 16]

DATA_COLLECTION_VARIANTS = {
    "with_misconfig": True,
    "without_misconfig": False,
}

DATA_COLLECTION_GRAPHS = {
    "set_1": {
        "vul_1k": "adsynth/experiment_params/vul_1k.json",
        "secure_1k": "adsynth/experiment_params/secure_1k.json",
    },
    "set_2": {
        "vul_5k": "adsynth/experiment_params/vul_5k.json",
        "secure_5k": "adsynth/experiment_params/secure_5k.json",
    },
}
```

## Injection schedules

| Schedule                     | Injection order                                                    |
| ---------------------------- | ------------------------------------------------------------------ |
| `session`                    | Session only                                                       |
| `session_permission`         | Session → Individual Permission → Group Permission                 |
| `session_permission_nesting` | Session → Individual Permission → Group Permission → Group Nesting |

Example:

```python
DATA_COLLECTION_SCHEDULES = {
    "session": ["session"],
    "session_permission": [
        "session",
        "i_perm",
        "g_perm",
    ],
    "session_permission_nesting": [
        "session",
        "i_perm",
        "g_perm",
        "nesting",
    ],
}
```

## Procedure

1. Open `ADSynth.py`.

2. Configure the required graph JSON files in `DATA_COLLECTION_GRAPHS`.

3. Add the required random seeds to `DATA_COLLECTION_SEEDS`.

4. Enable or disable the required initial graph variants in `DATA_COLLECTION_VARIANTS`.

5. Select the required injection schedules in `DATA_COLLECTION_SCHEDULES`.

6. Start Neo4j and confirm that the configured database credentials are correct.

7. Start the ADSynth CLI.

8. Run:

   ```text
   collect_data
   ```

9. Monitor the terminal output for the current graph, seed, variant, and schedule.

10. Review the generated CSV and DuckDB results after the experiments complete.

## Experiment workflow

For each configured combination, the application:

1. Sets the random seed.
2. Enables or disables initial misconfigurations.
3. Loads the selected ADSynth JSON configuration.
4. Generates the Active Directory graph.
5. Populates node tiers.
6. Builds graph tier caches.
7. Creates an experiment identifier.
8. Runs the configured sequence of misconfiguration injections.
9. Calculates exposure and structural indicators.
10. Exports the experiment results.

The configuration combinations are processed in the following order:

```text
Graph set
→ Graph configuration
→ Random seed
→ Initial graph variant
→ Injection schedule
```

## Experiment identifier

Each run is assigned an identifier using the graph, initial variant, schedule, seed, and timestamp.

Example:

```text
exp_vul_1k_with_misconfig_session_permission_nesting_seed_1_20260618_153000
```

The corresponding experiment name is stored in a readable format:

```text
vul_1k | with_misconfig | session_permission_nesting | seed=1
```

## Metrics collected

The workflow records metrics such as:

* misconfiguration step,
* normalized injection level `p`,
* reachable users,
* reachable computers,
* total exposure `X`,
* user exposure,
* computer exposure,
* HCI,
* CSM,
* TBS,
* PBCC,
* exposure change,
* indicator rise metrics,
* future-jump labels.

Across repeated realizations, the workflow also calculates:

```text
μ(p)  = mean exposure at injection level p
σ²(p) = exposure variance at injection level p
p*    = injection level where σ²(p) is highest
```

## Outputs

Each experiment is exported to a CSV file:

```text
analysis/csv/<experiment_id>.csv
```

Experiment metrics are also stored in:

```text
~/adsynth_metrics.duckdb
```

Example:

```text
analysis/csv/
└── exp_vul_1k_with_misconfig_session_permission_nesting_seed_1_20260618_153000.csv
```

## Reproducibility

Use the same:

* graph configuration JSON,
* security level,
* random seed,
* initial-misconfiguration variant,
* injection schedule,
* number of realizations,

to reproduce the same experiment conditions.

## Important notes

* Neo4j must be running before starting data collection.
* All configured JSON paths must exist.
* Use project-relative paths instead of machine-specific absolute paths.
* The current automated workflow runs with mitigation disabled.
* Large graph configurations may require substantial memory and execution time.
* Graph generation may replace the graph currently stored in Neo4j.
* A failure in one experiment can stop the remaining collection unless per-experiment error handling is added.

# Mode 3: UI Injection Without Mitigation

This mode injects misconfigurations while leaving **Enable Mitigation** unchecked.

## Supported injection types

| UI label | Internal identifier |
|---|---|
| Session | `session` |
| Individual Permission | `i_perm` |
| Group Permission | `g_perm` |
| Group Nesting | `nesting` |

## Injection schedules

### Isolated

Runs one injection family independently from the baseline graph.

Examples:

```text
Session only
Individual permission only
Group permission only
Group nesting only
```

The current UI validation permits only one selected injection type for each isolated run.

### Mixed

Mixed mode runs all four supported injection families in the same experiment.

Select at least two injection types before starting mixed mode.

The underlying implementation currently runs the standard mixed set in this order:

```text
session → individual permission → group permission → group nesting
```

### Sequence

Runs the selected injection types in the order returned by the UI:

```text
session → i_perm → g_perm → nesting
```

Only selected types are included.

Example:

```text
session → i_perm → nesting
```

## Procedure

1. Generate a graph or load an existing graph into Neo4j.
2. Choose **Isolated**, **Mixed**, or **Sequence**.
3. Select the required injection types.
4. Leave **Enable Mitigation** unchecked.
5. Select **Run Injection**.
6. Review the generated CSV and DuckDB records.

## Experiment measurements

Depending on the injection implementation, each step can record:

- misconfiguration step,
- normalized control parameter `p`,
- exposed users,
- exposed computers,
- total exposure `X`,
- user exposure,
- computer exposure,
- HCI,
- CSM,
- TBS,
- PBCC,
- change in exposure,
- rise metrics,
- future-jump labels.

Exposure is calculated as:

```text
X = (reachable users + reachable computers)
    / (total users + total computers)
```

Across repeated realizations, the system also calculates:

```text
μ(p)  = mean exposure
σ²(p) = exposure variance
p*    = p at maximum σ²(p)
```

## Outputs

Typical outputs are:

```text
analysis/csv/<experiment_id>.csv
~/adsynth_metrics.duckdb
```

Experiment identifiers follow patterns such as:

```text
exp_session_YYYYMMDD_HHMMSS
exp_i_perm_YYYYMMDD_HHMMSS
exp_g_perm_YYYYMMDD_HHMMSS
exp_nesting_YYYYMMDD_HHMMSS
exp_mixed_YYYYMMDD_HHMMSS
```

---

# Mode 4: UI Injection With Mitigation

This mode uses the same injection schedules but enables online mitigation.

## Procedure

1. Generate or load a graph.
2. Choose an injection schedule.
3. Select one or more injection types.
4. Check **Enable Mitigation**.
5. Select **Run Injection**.
6. Compare the resulting exposure trajectory with a corresponding non-mitigated run.


The injection implementation can call online mitigation after metrics are calculated for an injection step.

The following operations are done:

```text
Inject misconfiguration
→ calculate reachability and exposure
→ calculate indicators
→ evaluate mitigation trigger
→ remove or control selected risky relationships
→ continue experiment
```

## Mitigation state

The mitigation workflow may track:

- whether mitigation is enabled,
- mitigation trigger condition,
- mitigation budget,
- mitigation cost used,
- number of removed relationships,
- rise-streak threshold.

## Recommended comparison

For a controlled comparison, Generate  graph with the the following values constant:

- graph configuration,
- random seed,
- initial misconfiguration setting,
- injection mode,
- selected injection types,
- number of realizations.

Change only the mitigation setting:

```text
Run A: mitigation disabled
Run B: mitigation enabled
```

Compare:

- maximum exposure,
- largest exposure jump,
- critical point,
- cumulative mitigation cost,
- number of removed relationships,
- HCI, CSM, TBS, and PBCC trajectories.

---


# Mode 5: Prediction Through the CLI

Prediction runs logistic-regression models over experiment CSV files.

The CLI command is:

```text
runmodels <CSV_FOLDER>
```

## Start the ADSynth command interface

Run the module containing `MainMenu`:

```bash
cd <YOUR_PATH>/ADSynthMisconfig
PYTHONPATH=. python -m adsynth
```

At the ADSynth prompt:

```text
runmodels analysis/csv
```

When no folder is supplied, the command prompts for a CSV folder and defaults to:

```text
analysis/csv
```

## Required CSV columns

Each CSV must contain:

```text
experiment_id
```

The default label is:

```text
J_k5_z2p0
```

Common predictor columns are:

```text
HCI
CSM
TBS
PBCC
```

Useful optional columns include:

```text
iteration_id
step
p
X
```

## Models

The prediction suite evaluates 15 feature sets.

| Model | Features |
|---|---|
| M1_HCI_only | HCI |
| M2_CSM_only | CSM |
| M3_TBS_only | TBS |
| M4_PBCC_only | PBCC |
| M5_HCI_CSM | HCI, CSM |
| M6_HCI_TBS | HCI, TBS |
| M7_HCI_PBCC | HCI, PBCC |
| M8_CSM_TBS | CSM, TBS |
| M9_CSM_PBCC | CSM, PBCC |
| M10_TBS_PBCC | TBS, PBCC |
| M11_HCI_CSM_TBS | HCI, CSM, TBS |
| M12_HCI_CSM_PBCC | HCI, CSM, PBCC |
| M13_HCI_TBS_PBCC | HCI, TBS, PBCC |
| M14_CSM_TBS_PBCC | CSM, TBS, PBCC |
| M15_all | HCI, CSM, TBS, PBCC |

## Training process

For each CSV and model:

1. Remove rows with missing labels or required features.
2. Skip datasets that are empty or contain only one label class.
3. Split the data into 70% training and 30% testing.
4. Stratify the split by the jump label.
5. Train logistic regression.
6. Calculate classification and early-detection metrics.
7. Store metrics and prediction outputs in DuckDB.

## Prediction metrics

The model suite stores:

- ROC-AUC,
- PR-AUC,
- precision,
- recall,
- F1,
- accuracy,
- average lead time,
- median lead time,
- detection rate,
- true positives,
- false positives,
- true negatives,
- false negatives.

PR-AUC is especially useful when jump events are rare.

## Prediction outputs

The default database is:

```text
~/adsynth_metrics.duckdb
```

The prediction workflow writes to tables including:

```text
prediction_model_metrics
prediction_model_outputs

```


---

## Querying Results With DuckDB

Refer to [DuckDB queries](DuckDBQueries.md) 

---


## Analysing Graph in Neo4j

Refer to [Neo4j cypher queries](Neo4jCypherQueries.md) 

## Configuration Notes

### Avoid hard-coded paths

Replace paths such as:

```text
/Users/<username>/.../ADSynth/
```

with repository-relative paths.

Recommended Python pattern:

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "adsynth" / "experiment_params"
OUTPUT_DIR = PROJECT_ROOT / "generated_datasets"
CSV_DIR = PROJECT_ROOT / "analysis" / "csv"
```

```python
import os

password = os.getenv("NEO4J_PASSWORD", "")
```

### Create output directories

Before writing output:

```python
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)
```

---


## Example End-to-End Run

### 1. Start Neo4j

Start the local Neo4j database and verify APOC if graph import is required.

### 2. Open the UI

```bash
cd <YOUR_PATH>/ADSynthMisconfig
PYTHONPATH=. python ui/ADSynthUI.py
```

### 3. Generate a graph

Example configuration:

```text
JSON:                   adsynth/experiment_params/vul_1k.json
Security level:         High
Domain:                 TESTLAB.LOCALE
Random seed:            1
Initial misconfiguration: disabled
```

### 4. Run an unmitigated sequence

```text
Schedule: Sequence
Types:    Session, Individual Permission, Group Permission, Group Nesting
Mitigation: disabled
```

### 5. Run the matching mitigated sequence

Repeat the same setup with:

```text
Mitigation: enabled
```

### 6. Train prediction models

```bash
cd <YOUR_PATH>/ADSynthMisconfig
PYTHONPATH=. python -m adsynth
```

Then:

```text
runmodels analysis/csv
```

### 7. Inspect results

```bash
duckdb ~/adsynth_metrics.duckdb
```

```sql
SELECT *
FROM prediction_model_metrics
WHERE status = 'completed'
ORDER BY pr_auc DESC;
```

---

## Research Use

The framework is designed for experiments studying exposure growth and percolation-like transitions in Active Directory attack graphs under cumulative misconfiguration injection.


---

## License

License information can be found at [BSD 3-Clause License](../LICENSE)

## Acknowledgements

This project extends ADSynth with:

- a Tkinter graph-generation interface,
- configurable misconfiguration injection schedules,
- optional online mitigation,
- experiment export to CSV and DuckDB,
- early-jump prediction and evaluation.
