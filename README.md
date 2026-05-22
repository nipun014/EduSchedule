# Timetable Solver

An OR-Tools CP-SAT timetable generator for multi-class academic schedules. It assigns subjects, teachers, and rooms while respecting hard constraints such as teacher availability, room compatibility, subject frequency, and double-period rules.

This repository is organized to make the solver easy to understand, extend, and run on Windows or any Python environment supported by OR-Tools.

## Highlights

- Constraint-based scheduling with OR-Tools CP-SAT
- Teacher availability and room type enforcement
- Per-class, per-teacher, and per-room timetable exports
- JSON solution export with utilization statistics
- Pre-solver validation for early feasibility checks

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r timetable_solver/requirements.txt
python -m timetable_solver.solver
```

If you are using the included bootstrap environment, activate that environment instead of creating a new one.

## What You Get

Running the solver produces:

- Console timetables for each class
- `timetable.png` for class schedules
- `teacher_timetables.png` for teacher schedules
- `room_timetables.png` for room utilization
- `solution.json` with structured schedule data and metadata

These generated files are ignored by Git so the repository stays clean after each run.

## Repository Layout

- `timetable_solver/solver.py`: Main entry point that loads data, solves the model, validates results, and exports outputs
- `timetable_solver/model.py`: CP-SAT model with hard and soft constraints
- `timetable_solver/data_loader.py`: Loads and normalizes the sample dataset
- `timetable_solver/validator.py`: Pre- and post-solve validation helpers
- `timetable_solver/generator.py`: JSON export utilities
- `timetable_solver/sample_data.json`: Example dataset used by the solver
- `SYSTEM_OVERVIEW.md`: Full architecture and implementation guide

## How It Works

1. Load the sample data.
2. Validate the input for obvious conflicts or impossible demands.
3. Build the CP-SAT model with class, teacher, and room variables.
4. Solve the model with OR-Tools.
5. Validate the solution and export tables, images, and JSON.

The detailed model and constraint breakdown is documented in [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md).

## Customization

You can adapt the solver by editing `timetable_solver/sample_data.json` and the model logic in `timetable_solver/model.py`.

Common extension points include:

- New hard constraints for scheduling rules
- New soft preferences and weight tuning
- Alternative room types or teacher availability patterns
- Different export formats or visualizations

## Documentation

- [System Overview](SYSTEM_OVERVIEW.md)
- [Package README](timetable_solver/README.md)

## Notes

- The repository is currently set up for Python-based scheduling experiments, not production deployment.
- If you add new generated artifacts, extend `.gitignore` so they do not clutter commits.